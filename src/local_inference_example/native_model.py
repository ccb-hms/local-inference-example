"""Prototype: use the model's *native* tool-calling chat template (Qwen's
Hermes-style <tool_call> format) instead of outlines' constrained decoding,
then validate the free-generated JSON against the same AgentStep schema.

This exists to measure how often the "native format + pydantic validation"
approach fails compared to outlines' grammar-constrained approach in
model.py - see scripts/compare_failure_rates.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .agent import (
    FetchGeneCall,
    FinalAnswer,
    GetTimeCall,
    PlotGeneCall,
    ResolveGeneCall,
    SummarizeExpressionCall,
    _load_skill,
    SKILLS_DIR,
    AgentStep,
)
from .model import DEFAULT_MODEL, pick_device

TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)

_SKILL_CLASSES = [
    ResolveGeneCall,
    FetchGeneCall,
    SummarizeExpressionCall,
    PlotGeneCall,
    GetTimeCall,
]


def build_tool_schemas() -> list[dict]:
    """OpenAI/Hermes-style function schemas for every AgentStep variant,
    derived from the same pydantic models and skills/*.md descriptions the
    outlines path uses - so both approaches see an equivalent tool list."""
    descriptions = {_load_skill(p)["tool"]: _load_skill(p)["description"] for p in SKILLS_DIR.glob("*.md")}

    schemas = []
    for cls in _SKILL_CLASSES:
        name = cls.model_fields["tool"].annotation.__args__[0]
        schema = cls.model_json_schema()
        properties = {k: v for k, v in schema["properties"].items() if k != "tool"}
        required = [r for r in schema.get("required", []) if r != "tool"]
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": descriptions[name],
                    "parameters": {"type": "object", "properties": properties, "required": required},
                },
            }
        )

    final_schema = FinalAnswer.model_json_schema()
    schemas.append(
        {
            "type": "function",
            "function": {
                "name": "final_answer",
                "description": "Give the final answer to the user's question and stop.",
                "parameters": {
                    "type": "object",
                    "properties": {k: v for k, v in final_schema["properties"].items() if k != "tool"},
                    "required": ["answer"],
                },
            },
        }
    )
    return schemas


@dataclass
class ParsedCall:
    raw_text: str
    tool_call_json: str | None
    step: AgentStep | None
    error: str | None


def parse_and_validate(raw_text: str) -> ParsedCall:
    """Extract a <tool_call>{...}</tool_call> block from free-generated text
    and validate it against AgentStep. error is None only on full success."""
    match = TOOL_CALL_RE.search(raw_text)
    if not match:
        return ParsedCall(raw_text, None, None, "no <tool_call>...</tool_call> block found")

    tool_call_json = match.group(1)
    try:
        obj = json.loads(tool_call_json)
    except json.JSONDecodeError as e:
        return ParsedCall(raw_text, tool_call_json, None, f"invalid JSON: {e}")

    if "name" not in obj or "arguments" not in obj:
        return ParsedCall(raw_text, tool_call_json, None, "missing 'name' or 'arguments' key")
    if not isinstance(obj["arguments"], dict):
        return ParsedCall(raw_text, tool_call_json, None, "'arguments' is not a JSON object")

    try:
        step = AgentStep.model_validate({"step": {"tool": obj["name"], **obj["arguments"]}})
    except Exception as e:  # pydantic.ValidationError, plus the TypeError above's siblings
        return ParsedCall(raw_text, tool_call_json, None, f"schema validation failed: {e}")

    return ParsedCall(raw_text, tool_call_json, step, None)


class NativeLLM:
    """Mirrors LocalLLM's generate_step interface, but uses the tokenizer's
    native tools= chat template and free generation instead of outlines."""

    def __init__(self, model_name: str = DEFAULT_MODEL, max_new_tokens: int = 200, max_retries: int = 2):
        self.max_new_tokens = max_new_tokens
        self.max_retries = max_retries
        self.device = pick_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.hf_model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        self.tools = build_tool_schemas()

    def generate_raw(self, messages: list[dict], temperature: float = 0.7) -> str:
        prompt = self.tokenizer.apply_chat_template(
            messages, tools=self.tools, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        output = self.hf_model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        return self.tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)

    def generate_step(self, messages: list[dict]) -> AgentStep:
        """Retries on parse/validation failure, feeding the error back to
        the model - the realistic way you'd have to use this approach in
        production, since nothing prevents malformed output up front."""
        attempt_messages = list(messages)
        last_error = None
        for _ in range(self.max_retries + 1):
            raw_text = self.generate_raw(attempt_messages)
            parsed = parse_and_validate(raw_text)
            if parsed.error is None:
                return parsed.step
            last_error = parsed.error
            attempt_messages = attempt_messages + [
                {"role": "assistant", "content": raw_text},
                {"role": "user", "content": f"That was invalid: {last_error}. Try again."},
            ]
        raise ValueError(f"gave up after {self.max_retries + 1} attempts: {last_error}")
