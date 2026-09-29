"""Finds open-weight models that fit your hardware and links them on Hugging Face.

Wraps llmfit (https://github.com/AlexsJones/llmfit), which detects your CPU,
RAM, and GPU/VRAM and scores models by how well they'd run. Runs it via `uvx`
so nothing needs to be installed first.

llmfit's model database is largely community-uploaded (fine-tunes, quants,
etc. of a base model), and it has no way to filter by publisher reputation
or by whether a build is already quantized. By default this script keeps
only models that are both from KNOWN_PUBLISHERS (a fixed allowlist of
organizations that publish official base/instruct weights) and not already
quantized/converted (by name: no "gguf"/"mlx"/"awq"/"bnb"/"4bit"/etc. -
model.py loads weights directly with `AutoModelForCausalLM.from_pretrained`,
so those builds, which llmfit's scoring favors for their smaller memory
footprint, won't load here even from an official publisher). Pass
--all-publishers to see llmfit's raw, unfiltered recommendations instead;
both filters are heuristics, not guarantees, and will miss good models from
publishers not on the list or catch a repo whose name doesn't say "quantized"
but is one anyway.

Usage:
    uv run python scripts/find_hardware_model.py [--limit 5] [--use-case coding] [--all-publishers]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

HF_URL = "https://huggingface.co/{name}"

# HF namespaces that publish official base/instruct weights (as opposed to
# individual accounts' fine-tunes or quantizations of someone else's model).
# Lowercased for case-insensitive matching against llmfit's `provider` field.
KNOWN_PUBLISHERS = {
    "01-ai", "01.ai", "agentica-org", "ai21labs", "alibaba", "allenai",
    "bigcode", "bytedance-seed", "codellama", "cohereforai", "databricks",
    "deepseek-ai", "defog", "google", "huggingfaceh4", "ibm-granite",
    "internlm", "meta", "meta-llama", "microsoft", "mistralai",
    "nousresearch", "nvidia", "openbmb", "qwen", "redhatai", "salesforce",
    "snowflake", "stabilityai", "thudm", "tiiuae", "togethercomputer",
    "upstage", "xai-org", "zai-org",
}

# Repo-name substrings that mark an already-quantized/converted build (GGUF,
# MLX, AWQ, GPTQ, EXL2, bitsandbytes, ...). Even official publishers ship
# these alongside their original dense weights, and llmfit's scoring favors
# them since they're smaller - so provider alone isn't enough to catch them.
QUANT_MARKERS = (
    "gguf", "ggml", "mlx", "awq", "gptq", "exl2", "bnb", "4bit", "8bit",
    "int4", "int8", "nf4", "fp8", "quantized", "-q4", "-q5", "-q8",
)


def _is_quantized(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in QUANT_MARKERS)


def _fetch(use_case: str, fetch_limit: int) -> dict:
    try:
        result = subprocess.run(
            ["uvx", "llmfit", "recommend", "--json", "--limit", str(fetch_limit), "--use-case", use_case],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        sys.exit("uvx not found. Install uv: https://docs.astral.sh/uv/getting-started/installation/")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"llmfit failed:\n{exc.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5, help="Number of models to show (default: %(default)s)")
    parser.add_argument(
        "--use-case",
        choices=["general", "coding", "reasoning", "chat", "multimodal", "embedding"],
        default="general",
        help="Filter recommendations by use case (default: %(default)s)",
    )
    parser.add_argument(
        "--all-publishers",
        action="store_true",
        help="Skip the KNOWN_PUBLISHERS allowlist and show llmfit's raw recommendations",
    )
    args = parser.parse_args()

    # The allowlist only narrows results, so over-fetch from llmfit before
    # filtering down to --limit, rather than filtering an already-small page.
    fetch_limit = args.limit if args.all_publishers else max(args.limit * 20, 200)
    data = _fetch(args.use_case, fetch_limit)
    all_models = data.get("models", [])

    if args.all_publishers:
        models = all_models[: args.limit]
    else:
        models = [
            m
            for m in all_models
            if m.get("provider", "").lower() in KNOWN_PUBLISHERS and not _is_quantized(m["name"])
        ][: args.limit]

    if not models:
        print("No models fitting this use case on your hardware" + ("" if args.all_publishers else " from a known publisher") + ".")
        if not args.all_publishers:
            print("Try --all-publishers to see llmfit's full (unfiltered) recommendations.")
        return

    system = data.get("system", {})
    print(
        f"Detected hardware: {system.get('cpu_name', 'unknown CPU')}, "
        f"{system.get('total_ram_gb', '?')} GB RAM"
        + (f", {system.get('gpu_name')} ({system.get('gpu_vram_gb')} GB VRAM)" if system.get("has_gpu") else ", no GPU")
    )
    label = "llmfit's raw" if args.all_publishers else "known-publisher"
    print(f"\nTop {len(models)} {label} models for use case '{args.use_case}':\n")
    for model in models:
        name = model["name"]
        print(f"  {name}  [{model.get('fit_label', '?')}, score {model.get('score', '?')}]")
        print(f"    {HF_URL.format(name=name)}")

    print(
        "\nOnly dense, full-precision instruct models will load with this project's "
        "transformers-based loader (see model.py) - quantized GGUF/MLX/AWQ/EXL2 builds "
        "llmfit lists for other runtimes won't work here.\n"
        "Once you've picked one, run it with:\n"
        f"  uv run local-inference-example --model {models[0]['name']}"
    )


if __name__ == "__main__":
    main()
