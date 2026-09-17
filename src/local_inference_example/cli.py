"""Interactive CLI for the local-inference agent demo."""

from __future__ import annotations

from .agent import run_agent
from .model import DEFAULT_MODEL, LocalLLM


def main() -> None:
    print(f"Loading {DEFAULT_MODEL} (first run downloads it from Hugging Face)...")
    llm = LocalLLM()
    print(f"Ready on device: {llm.device}")
    print("Ask a question - try some arithmetic, or ask for the time. Ctrl-C to quit.\n")

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue

        result = run_agent(llm, query)
        for agent_step in result.steps[:-1]:
            print(f"  ...{agent_step.step.model_dump_json()}")
        print(result.answer)
