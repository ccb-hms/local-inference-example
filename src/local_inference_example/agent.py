"""A minimal tool-calling agent loop around a small local LLM.

Each step the model returns is constrained (via outlines, see model.py) to
be valid JSON matching the AgentStep schema below. The model can still pick
the wrong tool or bad arguments, but it can't return malformed JSON or an
unknown field - that's the failure mode a tiny model is most prone to, and
it's fixed structurally instead of by post-hoc parsing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, Union

from pydantic import BaseModel, Field

from .tools import TOOLS

MAX_STEPS = 4


# Curated to a handful of common GTEx tissues (of ~50 available) so the JSON
# schema constrains the model to a *valid* tissue name, not just a string -
# see tools.py for the full GTEx tissueSiteDetailId list this is drawn from.
Tissue = Literal[
    "Whole_Blood",
    "Liver",
    "Lung",
    "Muscle_Skeletal",
    "Brain_Cortex",
    "Breast_Mammary_Tissue",
    "Heart_Left_Ventricle",
    "Adipose_Subcutaneous",
    "Kidney_Cortex",
    "Pancreas",
]


class VolcanoCall(BaseModel):
    tool: Literal["volcano"]
    tissue_a: Tissue = Field(description="Baseline tissue")
    tissue_b: Tissue = Field(description="Comparison tissue")


class GetTimeCall(BaseModel):
    tool: Literal["get_time"]


class FinalAnswer(BaseModel):
    tool: Literal["final_answer"]
    answer: str = Field(max_length=300)


class AgentStep(BaseModel):
    step: Union[VolcanoCall, GetTimeCall, FinalAnswer] = Field(discriminator="tool")


SYSTEM_PROMPT = """You are a helpful assistant with access to tools. On each \
turn, respond with a single JSON object describing your next step: either a \
tool call or your final answer.

Available tools:
- volcano: compare a panel of tissue-marker genes between two tissues using \
real public gene-expression data (GTEx) and produce a volcano plot (log2 \
fold change vs. significance), e.g. \
{"tool": "volcano", "tissue_a": "Liver", "tissue_b": "Pancreas"}
- get_time: get the current local date and time, e.g. {"tool": "get_time"}

Once you know the answer, respond with: {"tool": "final_answer", "answer": "..."}

Respond with exactly one JSON object and nothing else.
"""

# A tiny model needs to see one full round-trip to reliably follow up a tool
# call with a final_answer instead of, say, calling another tool out of
# habit. This one-shot example is prepended to every conversation.
FEW_SHOT_EXAMPLE: list[dict[str, str]] = [
    {"role": "user", "content": "Compare gene expression between blood and pancreas."},
    {
        "role": "assistant",
        "content": '{"tool": "volcano", "tissue_a": "Whole_Blood", "tissue_b": "Pancreas"}',
    },
    {
        "role": "user",
        "content": (
            "Observation: Compared 12 marker genes between Whole_Blood and Pancreas. "
            "Most enriched in Pancreas: INS (log2FC=13.17). Most enriched in Whole_Blood: "
            "HBB (log2FC=-12.54). Interactive volcano plot saved to "
            "output/volcano_Whole_Blood_vs_Pancreas.html"
        ),
    },
    {
        "role": "assistant",
        "content": (
            '{"tool": "final_answer", "answer": "INS (insulin) is the most pancreas-'
            'enriched marker gene and HBB (hemoglobin) the most blood-enriched - see '
            'output/volcano_Whole_Blood_vs_Pancreas.html"}'
        ),
    },
]


class ChatModel(Protocol):
    def generate_step(self, messages: list[dict[str, str]]) -> AgentStep: ...


@dataclass
class AgentResult:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)


def _run_tool(step: Union[VolcanoCall, GetTimeCall]) -> str:
    tool = TOOLS[step.tool]
    kwargs = step.model_dump(exclude={"tool"})
    return str(tool(**kwargs))


def run_agent(llm: ChatModel, query: str, max_steps: int = MAX_STEPS) -> AgentResult:
    """Run the tool-call loop until a final_answer step or the step limit."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *FEW_SHOT_EXAMPLE,
        {"role": "user", "content": query},
    ]
    steps: list[AgentStep] = []
    last_call: str | None = None
    last_observation: str | None = None

    for _ in range(max_steps):
        agent_step = llm.generate_step(messages)
        step = agent_step.step
        steps.append(agent_step)
        messages.append({"role": "assistant", "content": step.model_dump_json()})

        if isinstance(step, FinalAnswer):
            return AgentResult(answer=step.answer, steps=steps)

        # A small model can get stuck re-issuing the same tool call instead
        # of moving on to a final_answer. Rather than burn the whole step
        # budget on that, fall back to the observation it already has.
        call = step.model_dump_json()
        if call == last_call:
            return AgentResult(answer=last_observation or "(no result)", steps=steps)
        last_call = call

        last_observation = _run_tool(step)
        messages.append({"role": "user", "content": f"Observation: {last_observation}"})

    return AgentResult(
        answer=f"(gave up after {max_steps} steps; last observation: {last_observation})",
        steps=steps,
    )
