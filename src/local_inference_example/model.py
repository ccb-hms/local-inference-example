"""Loads a small local model and generates JSON-schema-constrained agent steps."""

from __future__ import annotations

import outlines
import torch
from huggingface_hub import try_to_load_from_cache
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

from .agent import AgentStep

# ~7GB download, runs comfortably on a laptop CPU/MPS/GPU - a plain
# text-only causal LM, no multimodal encoders to carry around. The JSON
# schema constraint (see AgentStep) guarantees valid *syntax* regardless of
# model size, but smaller models are noticeably less reliable at choosing
# the right tool.
MODEL_SIZES = {
    "3.8b": "microsoft/Phi-3.5-mini-instruct",
}
DEFAULT_MODEL_SIZE = "3.8b"
DEFAULT_MODEL = MODEL_SIZES[DEFAULT_MODEL_SIZE]


def _already_cached(model_name: str) -> bool:
    """True if this model's weights are already in the local Hugging Face
    cache. `from_pretrained` would find them either way, but by default it
    still makes a network call first to check for a newer revision - which
    can stall or, on a flaky connection, fall back to re-downloading. Skip
    that check entirely once we know the files are already on disk."""
    return try_to_load_from_cache(model_name, "config.json") is not None


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
        self.model_name = model_name  # the HF repo id, for /api/status - distinct from self.model below
        self.max_new_tokens = max_new_tokens  # cap on how much text the model can generate per step
        self.device = pick_device()
        if self.device == "cpu":
            # Measured on a laptop CPU: ~60s per agent step for this model,
            # so a multi-step query can take several minutes. Say so up
            # front rather than let it look hung.
            print(
                "No GPU (CUDA/MPS) detected - running on CPU. This model is "
                "slow on CPU: expect roughly a minute per agent step, so a "
                "multi-step question can take several minutes."
            )
        # Once we've downloaded a model, load it straight from the local
        # cache instead of asking the Hub each time whether a newer revision
        # exists - so a plain `uv run` never re-downloads it.
        local_only = _already_cached(model_name)
        # huggingface_hub prints its own per-file tqdm bars for the actual
        # download; this outer bar just tracks the two loading steps so
        # there's visible progress even once the weights are cached.
        with tqdm(total=2, desc=f"Loading {model_name}", unit="step") as progress:
            self.tokenizer = AutoTokenizer.from_pretrained(  # converts text <-> tokens
                model_name, local_files_only=local_only
            )
            progress.update(1)
            # trust_remote_code=False (the default): phi3 is natively built
            # into transformers, and the repo's own modeling_phi3.py is
            # stale against current transformers internals (it calls a
            # DynamicCache API that no longer exists) - the native
            # implementation is both safer and the one that actually works.
            hf_model = AutoModelForCausalLM.from_pretrained(  # downloads the model (first run only)
                model_name, local_files_only=local_only
            ).to(self.device)
            progress.update(1)
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
