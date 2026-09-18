"""The agent's toolbox: one importable module per tool, each a standalone
function the agent loop can call. `TOOLS` is the registry the agent looks
calls up in; see ../skills/ for the natural-language description of each
tool that's shown to the model.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ToolResult:
    """What every tool hands back after it runs."""

    text: str  # a short, plain-English summary shown in the chat
    chart: dict | None = None  # a Vega-Lite spec (alt.Chart.to_dict()), if this tool made one
    api_url: str | None = None  # the exact request URL this call made, if it called an API
    raw_data: object | None = None  # a small, JSON-serializable look at the real data behind `text`


# Imported down here (not at the top) because each tool module imports ToolResult from
# this same file - moving these up would create a circular import.
from .fetch_gene_expression import fetch_gene_expression  # noqa: E402
from .get_time import get_time  # noqa: E402
from .plot_gene_expression import plot_gene_expression  # noqa: E402
from .resolve_gene import resolve_gene  # noqa: E402
from .summarize_expression import summarize_expression  # noqa: E402

# Lets the agent look up a tool function by the name the model chose.
TOOLS: dict[str, Callable[..., ToolResult]] = {
    "resolve_gene": resolve_gene,
    "fetch_gene_expression": fetch_gene_expression,
    "summarize_expression": summarize_expression,
    "plot_gene_expression": plot_gene_expression,
    "get_time": get_time,
}

__all__ = [
    "TOOLS",
    "ToolResult",
    "resolve_gene",
    "fetch_gene_expression",
    "summarize_expression",
    "plot_gene_expression",
    "get_time",
]
