"""A minimal tool-calling agent loop around a small local LLM.

Each step the model returns is constrained (via outlines, see model.py) to
be valid JSON matching the AgentStep schema below. The model can still pick
the wrong tool or bad arguments, but it can't return malformed JSON or an
unknown field - that's the failure mode a tiny model is most prone to, and
it's fixed structurally instead of by post-hoc parsing.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, Union
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, Field

from .tools import TOOLS, ToolResult

MAX_STEPS = 7  # give up after this many tool calls, so a confused model can't loop forever
SKILLS_DIR = Path(__file__).parent / "skills"


def _load_skill(path: Path) -> dict[str, str]:
    """Parse a skills/*.md file's `key: value` frontmatter (between the
    `---` markers) into a dict. The prose below the frontmatter is for
    humans reading the repo; only the frontmatter feeds the prompt."""
    _, frontmatter, _ = path.read_text().split("---", 2)  # text between the two "---" lines
    fields = {}
    for line in frontmatter.strip().splitlines():  # one "key: value" pair per line
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def _build_tool_list() -> str:
    """One bullet per skills/*.md file, in the exact wording that file
    declares - editing a skill file changes what the model is told, with no
    Python change required."""
    skills = [_load_skill(path) for path in sorted(SKILLS_DIR.glob("*.md"))]  # one file per tool
    return "\n".join(f"- {s['tool']}: {s['description']}, e.g. {s['call']}" for s in skills)


# Each of these classes describes the exact shape of one kind of tool call the model can
# make - which fields it needs and what values are allowed. The model's output is checked
# against these shapes, so it can't send a call that's missing a field or has a typo'd name.
class ResolveGeneCall(BaseModel):
    tool: Literal["resolve_gene"]
    gene: str = Field(max_length=20, description="A gene symbol, e.g. 'BRCA1'")


class FetchGeneCall(BaseModel):
    tool: Literal["fetch_gene_expression"]
    gene: str = Field(max_length=20, description="A gene symbol, e.g. 'BRCA1'")


class SummarizeExpressionCall(BaseModel):
    tool: Literal["summarize_expression"]
    gene: str = Field(max_length=20, description="A gene symbol, e.g. 'BRCA1'")


# The full list of valid GTEx tissue IDs, so highlight_tissue below is
# constrained to a real tissue - not just any string - the same way a real
# API's enum parameter would be.
Tissue = Literal[
    "Adipose_Subcutaneous", "Adipose_Visceral_Omentum", "Adrenal_Gland", "Artery_Aorta",
    "Artery_Coronary", "Artery_Tibial", "Bladder", "Brain_Amygdala",
    "Brain_Anterior_cingulate_cortex_BA24", "Brain_Caudate_basal_ganglia",
    "Brain_Cerebellar_Hemisphere", "Brain_Cerebellum", "Brain_Cortex",
    "Brain_Frontal_Cortex_BA9", "Brain_Hippocampus", "Brain_Hypothalamus",
    "Brain_Nucleus_accumbens_basal_ganglia", "Brain_Putamen_basal_ganglia",
    "Brain_Spinal_cord_cervical_c-1", "Brain_Substantia_nigra", "Breast_Mammary_Tissue",
    "Cells_Cultured_fibroblasts", "Cells_EBV-transformed_lymphocytes",
    "Cells_Transformed_fibroblasts", "Cervix_Ectocervix", "Cervix_Endocervix",
    "Colon_Sigmoid", "Colon_Transverse", "Esophagus_Gastroesophageal_Junction",
    "Esophagus_Mucosa", "Esophagus_Muscularis", "Fallopian_Tube", "Heart_Atrial_Appendage",
    "Heart_Left_Ventricle", "Kidney_Cortex", "Kidney_Medulla", "Liver", "Lung",
    "Minor_Salivary_Gland", "Muscle_Skeletal", "Nerve_Tibial", "Ovary", "Pancreas",
    "Pituitary", "Prostate", "Skin_Not_Sun_Exposed_Suprapubic", "Skin_Sun_Exposed_Lower_leg",
    "Small_Intestine_Terminal_Ileum", "Spleen", "Stomach", "Testis", "Thyroid", "Uterus",
    "Vagina", "Whole_Blood",
]


class PlotGeneCall(BaseModel):
    tool: Literal["plot_gene_expression"]
    gene: str = Field(max_length=20, description="A gene symbol, e.g. 'BRCA1'")
    highlight_tissue: Tissue | None = Field(
        default=None, description="Optional: a tissue to highlight in red on the chart"
    )


class GetTimeCall(BaseModel):
    tool: Literal["get_time"]


class FinalAnswer(BaseModel):
    """Not a tool call - this is how the model signals "I'm done, here's the answer"."""

    tool: Literal["final_answer"]
    answer: str = Field(max_length=300)


ToolCall = Union[
    ResolveGeneCall, FetchGeneCall, SummarizeExpressionCall, PlotGeneCall, GetTimeCall
]


class AgentStep(BaseModel):
    """Exactly one of the shapes above - whatever the model decides to do next.
    `discriminator="tool"` tells it to pick the shape by looking at the "tool" field."""

    step: Union[
        ResolveGeneCall,
        FetchGeneCall,
        SummarizeExpressionCall,
        PlotGeneCall,
        GetTimeCall,
        FinalAnswer,
    ] = Field(discriminator="tool")


SYSTEM_PROMPT = f"""You are a helpful assistant with access to tools. On each \
turn, respond with a single JSON object describing your next step: either a \
tool call or your final answer.

Available tools:
{_build_tool_list()}

Once you know the answer, respond with: {{"tool": "final_answer", "answer": "..."}}

Respond with exactly one JSON object and nothing else.
"""

# A tiny model needs to see a full round-trip - including a multi-tool
# chain and a failure - to reliably follow up with a final_answer instead
# of, say, calling another tool out of habit. These examples are prepended
# to every conversation.
FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {"role": "user", "content": "Where is BRCA1 expressed?"},
    {"role": "assistant", "content": '{"tool": "resolve_gene", "gene": "BRCA1"}'},
    {
        "role": "user",
        "content": (
            "Observation: Resolved 'BRCA1' to GENCODE ID ENSG00000012048.23 "
            "(canonical symbol: BRCA1)."
        ),
    },
    {"role": "assistant", "content": '{"tool": "fetch_gene_expression", "gene": "BRCA1"}'},
    {
        "role": "user",
        "content": (
            "Observation: Fetched 19616 real per-sample TPM values for BRCA1 "
            "across 54 GTEx tissues."
        ),
    },
    {"role": "assistant", "content": '{"tool": "summarize_expression", "gene": "BRCA1"}'},
    {
        "role": "user",
        "content": (
            "Observation: BRCA1: highest median expression in "
            "Cells_EBV-transformed_lymphocytes (20.93 TPM), 15.5x the median across "
            "all 54 tissues."
        ),
    },
    {"role": "assistant", "content": '{"tool": "plot_gene_expression", "gene": "BRCA1"}'},
    {
        "role": "user",
        "content": "Observation: Rendered BRCA1's expression chart across GTEx tissues.",
    },
    {
        "role": "assistant",
        "content": (
            '{"tool": "final_answer", "answer": "BRCA1 is most highly expressed in '
            'EBV-transformed lymphocytes, about 15.5x the median across all 54 GTEx '
            'tissues - see the chart"}'
        ),
    },
    {"role": "user", "content": "How about the gene FOOBARBAZ?"},
    {"role": "assistant", "content": '{"tool": "resolve_gene", "gene": "FOOBARBAZ"}'},
    {
        "role": "user",
        "content": "Observation: error: 'FOOBARBAZ' doesn't match any gene symbol in GTEx",
    },
    {
        "role": "assistant",
        "content": (
            '{"tool": "final_answer", "answer": "I couldn\'t find a gene called '
            'FOOBARBAZ in GTEx - check the spelling of the gene symbol"}'
        ),
    },
]


class ChatModel(Protocol):
    """Anything with a generate_step method can drive the agent loop - lets tests
    swap in a fake model instead of loading the real (slow) one."""

    def generate_step(self, messages: list[dict[str, str]]) -> AgentStep: ...


@dataclass
class TranscriptEntry:
    kind: Literal["thinking", "action", "api_call", "observation", "final"]
    text: str
    # What to show in the "inspector" panel if this entry is the active one:
    # {"type": "code" | "api" | "data" | "json", "language": ..., "content": ...}
    detail: dict | None = None
    # Set only on the observation entry that produced/updated the chart -
    # lets a streaming consumer render it the moment it's ready, not just
    # once the whole run finishes.
    chart: dict | None = None


def _describe_call(step: ToolCall) -> str:
    """A one-line, plain-English caption for whichever tool call the model just made."""
    if isinstance(step, ResolveGeneCall):
        return f"Calling resolve_gene(gene='{step.gene}') - looking up its GENCODE ID..."
    if isinstance(step, FetchGeneCall):
        return f"Calling fetch_gene_expression(gene='{step.gene}') - querying the GTEx API..."
    if isinstance(step, SummarizeExpressionCall):
        return f"Calling summarize_expression(gene='{step.gene}') - computing the stats..."
    if isinstance(step, PlotGeneCall):
        highlight = f", highlighting '{step.highlight_tissue}'" if step.highlight_tissue else ""
        return f"Calling plot_gene_expression(gene='{step.gene}'{highlight}) - building the chart..."
    return "Calling get_time() - reading the system clock..."


def _call_detail(step: Union[ToolCall, FinalAnswer]) -> dict:
    """What actually runs for this step: the tool's own source code, or (for
    final_answer, which has no tool function) the raw JSON the model
    produced."""
    if isinstance(step, FinalAnswer):
        return {"type": "json", "language": "json", "content": step.model_dump_json(indent=2)}
    try:
        content = inspect.getsource(TOOLS[step.tool])  # read the tool function's own source code
    except (OSError, TypeError, KeyError):
        content = "# source unavailable"
    return {"type": "code", "language": "python", "content": content}


def _api_detail(api_url: str) -> dict:
    """The request that actually ran, broken into method/endpoint/params
    instead of one long query string."""
    parts = urlsplit(api_url)  # break the URL into scheme/host/path/query pieces
    payload = {
        "method": "GET",
        "endpoint": f"{parts.scheme}://{parts.netloc}{parts.path}",
        "params": dict(parse_qsl(parts.query)),  # the "?key=value&..." part, as a dict
    }
    return {"type": "api", "language": "json", "content": json.dumps(payload, indent=2)}


def _data_detail(result: ToolResult) -> dict | None:
    """A real look at the data behind this tool's text summary, if it
    captured one."""
    if result.raw_data is None:
        return None
    return {
        "type": "data",
        "language": "json",
        "content": json.dumps(result.raw_data, indent=2, default=str),
    }


def run_agent_stream(llm: ChatModel, query: str, max_steps: int = MAX_STEPS):
    """Run the tool-call loop, yielding each TranscriptEntry the instant
    it's produced - the real basis for "live" narration."""
    # The running back-and-forth "conversation" fed to the model each turn: the
    # instructions, a few worked examples, then the user's real question.
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *FEW_SHOT_EXAMPLES,
        {"role": "user", "content": query},
    ]
    last_call: str | None = None
    last_result: ToolResult | None = None

    for step_num in range(max_steps):  # keep asking the model "what next?" up to max_steps times
        yield TranscriptEntry(
            "thinking",
            "Reading your question..." if step_num == 0 else "Deciding what to do next...",
        )
        agent_step = llm.generate_step(messages)  # ask the model to decide its next step
        step = agent_step.step
        messages.append({"role": "assistant", "content": step.model_dump_json()})  # remember its choice

        if isinstance(step, FinalAnswer):  # the model says it's done
            yield TranscriptEntry(
                "action", "Calling final_answer(...) - wrapping up...", _call_detail(step)
            )
            yield TranscriptEntry("final", step.answer, _call_detail(step))
            return

        yield TranscriptEntry("action", _describe_call(step), _call_detail(step))

        # A small model can get stuck re-issuing the same tool call instead
        # of moving on to a final_answer. Rather than burn the whole step
        # budget on that, fall back to the observation it already has.
        call = step.model_dump_json()
        if call == last_call:
            yield TranscriptEntry("final", last_result.text if last_result else "(no result)")
            return
        last_call = call

        tool = TOOLS[step.tool]  # look up the actual Python function for this tool name
        last_result = tool(**step.model_dump(exclude={"tool"}))  # run it with the chosen arguments
        if last_result.api_url:  # show the real web request this tool made, if any
            yield TranscriptEntry(
                "api_call", last_result.api_url, _api_detail(last_result.api_url)
            )
        yield TranscriptEntry(
            "observation",
            f"Data returned: {last_result.text}",
            _data_detail(last_result),
            chart=last_result.chart,
        )
        # Feed the result back in, so the model's next decision accounts for what just happened.
        messages.append({"role": "user", "content": f"Observation: {last_result.text}"})

    # Ran out of steps without the model reaching a final answer - report the last thing we know.
    yield TranscriptEntry(
        "final",
        f"(gave up after {max_steps} steps; last observation: "
        f"{last_result.text if last_result else 'none'})",
    )
