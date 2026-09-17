"""Loads a small local model and generates JSON-schema-constrained agent steps."""

from __future__ import annotations

import outlines
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .agent import AgentStep

# ~3GB download, runs comfortably on a laptop CPU. The JSON schema constraint
# (see AgentStep) guarantees valid *syntax* regardless of model size, but
# smaller models are noticeably less reliable at choosing the right tool -
# Qwen2.5-0.5B-Instruct, for example, frequently loops on get_time instead of
# giving a final_answer. 1.5B is close to the sweet spot for this demo; try
# dropping to Qwen/Qwen2.5-0.5B-Instruct to show that failure mode live.
DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class LocalLLM:
    """Wraps a small instruction-tuned model with outlines' constrained decoding."""

    def __init__(self, model_name: str = DEFAULT_MODEL, max_new_tokens: int = 200):
        self.max_new_tokens = max_new_tokens
        self.device = pick_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        hf_model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        self.model = outlines.from_transformers(hf_model, self.tokenizer)
        self.generator = outlines.Generator(self.model, AgentStep)

    def generate_step(self, messages: list[dict[str, str]]) -> AgentStep:
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        raw_json = self.generator(prompt, max_new_tokens=self.max_new_tokens)
        return AgentStep.model_validate_json(raw_json)
