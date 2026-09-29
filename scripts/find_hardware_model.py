"""Finds open-weight models that fit your hardware and links them on Hugging Face.

Wraps llmfit (https://github.com/AlexsJones/llmfit), which detects your CPU,
RAM, and GPU/VRAM and scores models by how well they'd run. Runs it via `uvx`
so nothing needs to be installed first.

Only dense, non-quantized instruct models are good matches for this project:
model.py loads weights directly with `AutoModelForCausalLM.from_pretrained`,
so GGUF/MLX/AWQ/EXL2 builds llmfit also recommends (for runtimes like
llama.cpp or MLX) won't load here.

Usage:
    uv run python scripts/find_hardware_model.py [--limit 5] [--use-case coding]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

HF_URL = "https://huggingface.co/{name}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5, help="Number of models to show (default: %(default)s)")
    parser.add_argument(
        "--use-case",
        choices=["general", "coding", "reasoning", "chat", "multimodal", "embedding"],
        default="general",
        help="Filter recommendations by use case (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        result = subprocess.run(
            [
                "uvx",
                "llmfit",
                "recommend",
                "--json",
                "--limit",
                str(args.limit),
                "--use-case",
                args.use_case,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        sys.exit("uvx not found. Install uv: https://docs.astral.sh/uv/getting-started/installation/")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"llmfit failed:\n{exc.stderr}")

    data = json.loads(result.stdout)
    models = data.get("models", [])
    if not models:
        print("llmfit found no models fitting this use case on your hardware.")
        return

    system = data.get("system", {})
    print(
        f"Detected hardware: {system.get('cpu_name', 'unknown CPU')}, "
        f"{system.get('total_ram_gb', '?')} GB RAM"
        + (f", {system.get('gpu_name')} ({system.get('gpu_vram_gb')} GB VRAM)" if system.get("has_gpu") else ", no GPU")
    )
    print(f"\nTop {len(models)} models for use case '{args.use_case}':\n")
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
