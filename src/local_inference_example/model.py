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
    """Use a GPU if one's available (much faster), otherwise fall back to the CPU."""
    if torch.cuda.is_available():
        return "cuda"  # NVIDIA GPU
    if torch.backends.mps.is_available():
        return "mps"  # Apple Silicon GPU
    return "cpu"


class LocalLLM:
    """Wraps a small instruction-tuned model with outlines' constrained decoding."""

    def __init__(self, model_name: str = DEFAULT_MODEL, max_new_tokens: int = 200):
        self.max_new_tokens = max_new_tokens  # cap on how much text the model can generate per step
        self.device = pick_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)  # converts text <-> tokens
        hf_model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)  # downloads the model
        self.model = outlines.from_transformers(hf_model, self.tokenizer)
        # A generator that's guaranteed to only ever produce valid AgentStep JSON.
        self.generator = outlines.Generator(self.model, AgentStep)

    def generate_step(self, messages: list[dict[str, str]]) -> AgentStep:
        """Turn the conversation so far into one validated next step."""
        prompt = self.tokenizer.apply_chat_template(  # format for this model's expected chat style
            messages, tokenize=False, add_generation_prompt=True
        )
        raw_json = self.generator(prompt, max_new_tokens=self.max_new_tokens)  # run the model
        return AgentStep.model_validate_json(raw_json)  # parse its output into a typed object
