"""Compares two ways of getting a structured tool call out of Qwen2.5-Instruct:

1. outlines: grammar-constrained decoding directly against the AgentStep
   pydantic schema (what model.py does today).
2. native: the model's own <tool_call> chat-template format, free-generated,
   then parsed and validated against the same AgentStep schema.

For each approach we sample N completions per prompt (temperature > 0, no
retries) and record whether the raw output was schema-valid on the first
try. This isolates "how often does raw generation conform to the schema" -
retries are a separate mitigation, not counted as success here.

Usage: uv run python scripts/compare_failure_rates.py
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import outlines
from transformers import AutoModelForCausalLM, AutoTokenizer

from local_inference_example.agent import AgentStep, SYSTEM_PROMPT
from local_inference_example.model import DEFAULT_MODEL as _DEFAULT_MODEL, pick_device
from local_inference_example.native_model import build_tool_schemas, parse_and_validate

MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_MODEL

N_SAMPLES = 8
MAX_NEW_TOKENS = 100
TEMPERATURE = 0.7

TEST_QUERIES = [
    "Where is TP53 expressed?",
    "What time is it?",
    "Plot the expression of MYC and highlight the liver",
    "How about the gene XYZQRS123?",
]

# Same demo trace as agent.FEW_SHOT_EXAMPLES, expressed in outlines' bare-JSON
# style (matches SYSTEM_PROMPT's convention).
OUTLINES_FEW_SHOT = [
    {"role": "user", "content": "Where is BRCA1 expressed?"},
    {"role": "assistant", "content": '{"tool": "resolve_gene", "gene": "BRCA1"}'},
    {"role": "user", "content": "Observation: Resolved 'BRCA1' to GENCODE ID ENSG00000012048.23."},
    {"role": "assistant", "content": '{"tool": "final_answer", "answer": "BRCA1 is a DNA repair gene."}'},
]

# The same trace, expressed the way the native <tool_call> chat template
# expects it (assistant tool_calls + tool-role observations), so native
# generation gets equivalent in-context conditioning rather than none.
NATIVE_FEW_SHOT = [
    {"role": "user", "content": "Where is BRCA1 expressed?"},
    {
        "role": "assistant",
        "tool_calls": [{"function": {"name": "resolve_gene", "arguments": {"gene": "BRCA1"}}}],
    },
    {"role": "tool", "content": "Resolved 'BRCA1' to GENCODE ID ENSG00000012048.23."},
    {
        "role": "assistant",
        "tool_calls": [
            {"function": {"name": "final_answer", "arguments": {"answer": "BRCA1 is a DNA repair gene."}}}
        ],
    },
]


def run_outlines_trial(generator, tokenizer, query: str) -> tuple[bool, str]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *OUTLINES_FEW_SHOT,
        {"role": "user", "content": query},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    raw_json = generator(prompt, max_new_tokens=MAX_NEW_TOKENS)
    try:
        AgentStep.model_validate_json(raw_json)
        return True, "ok"
    except Exception as e:
        return False, f"schema validation failed: {e}"


NATIVE_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools. Every tool call must "
    "include an \"arguments\" object, even for a tool that takes no "
    "parameters - use an empty object, e.g. "
    '{"name": "get_time", "arguments": {}}.'
)


def run_native_trial(hf_model, tokenizer, tools, device, query: str) -> tuple[bool, str]:
    messages = [
        {"role": "system", "content": NATIVE_SYSTEM_PROMPT},
        *NATIVE_FEW_SHOT,
        {"role": "user", "content": query},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, tools=tools, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    output = hf_model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=True,
        temperature=TEMPERATURE,
        pad_token_id=tokenizer.eos_token_id,
    )
    raw_text = tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
    parsed = parse_and_validate(raw_text)
    return parsed.error is None, (parsed.error or "ok")


def main() -> None:
    device = pick_device()
    print(f"device: {device}, model: {MODEL_NAME}\n")

    print("Loading model for outlines (constrained decoding)...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    hf_model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(device)
    outlines_model = outlines.from_transformers(hf_model, tokenizer)
    generator = outlines.Generator(outlines_model, AgentStep)

    tools = build_tool_schemas()

    results: dict[str, Counter] = {"outlines": Counter(), "native": Counter()}
    failure_examples: dict[str, list[str]] = {"outlines": [], "native": []}

    for query in TEST_QUERIES:
        print(f"\n=== query: {query!r} ===")

        t0 = time.time()
        for i in range(N_SAMPLES):
            ok, reason = run_outlines_trial(generator, tokenizer, query)
            results["outlines"]["ok" if ok else "fail"] += 1
            if not ok:
                failure_examples["outlines"].append(f"{query!r}: {reason}")
            print(f"  outlines [{i+1}/{N_SAMPLES}]: {'OK' if ok else 'FAIL - ' + reason}")
        print(f"  outlines: {time.time() - t0:.1f}s for {N_SAMPLES} samples")

        t0 = time.time()
        for i in range(N_SAMPLES):
            ok, reason = run_native_trial(hf_model, tokenizer, tools, device, query)
            results["native"]["ok" if ok else "fail"] += 1
            if not ok:
                failure_examples["native"].append(f"{query!r}: {reason}")
            print(f"  native   [{i+1}/{N_SAMPLES}]: {'OK' if ok else 'FAIL - ' + reason}")
        print(f"  native: {time.time() - t0:.1f}s for {N_SAMPLES} samples")

    print("\n=== Summary ===")
    for approach in ["outlines", "native"]:
        ok = results[approach]["ok"]
        total = ok + results[approach]["fail"]
        print(f"{approach:10s}: {ok}/{total} valid on first try ({100 * ok / total:.0f}%)")
        for example in failure_examples[approach]:
            print(f"    failed: {example}")


if __name__ == "__main__":
    main()
