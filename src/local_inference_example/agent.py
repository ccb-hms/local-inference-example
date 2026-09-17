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


class CalculatorCall(BaseModel):
    tool: Literal["calculator"]
    expression: str = Field(description="An arithmetic expression, e.g. '12 * (3 + 4)'")


class GetTimeCall(BaseModel):
    tool: Literal["get_time"]


class FinalAnswer(BaseModel):
    tool: Literal["final_answer"]
    answer: str


class AgentStep(BaseModel):
    step: Union[CalculatorCall, GetTimeCall, FinalAnswer] = Field(discriminator="tool")


SYSTEM_PROMPT = """You are a helpful assistant with access to tools. On each \
turn, respond with a single JSON object describing your next step: either a \
tool call or your final answer.

Available tools:
- calculator: evaluate an arithmetic expression, e.g. {"tool": "calculator", "expression": "12 * (3 + 4)"}
- get_time: get the current local date and time, e.g. {"tool": "get_time"}

Once you know the answer, respond with: {"tool": "final_answer", "answer": "..."}

Respond with exactly one JSON object and nothing else.
"""

# A tiny model needs to see one full round-trip to reliably follow up a tool
# call with a final_answer instead of, say, calling another tool out of
# habit. This one-shot example is prepended to every conversation.
FEW_SHOT_EXAMPLE: list[dict[str, str]] = [
    {"role": "user", "content": "What is 6 times 7?"},
    {"role": "assistant", "content": '{"tool": "calculator", "expression": "6 * 7"}'},
    {"role": "user", "content": "Observation: 42"},
    {"role": "assistant", "content": '{"tool": "final_answer", "answer": "42"}'},
]


class ChatModel(Protocol):
    def generate_step(self, messages: list[dict[str, str]]) -> AgentStep: ...


@dataclass
class AgentResult:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)


def _run_tool(step: Union[CalculatorCall, GetTimeCall]) -> str:
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
