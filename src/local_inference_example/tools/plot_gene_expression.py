"""Tool: chart a gene's expression data.

The visualization step - owns presentation only, and touches no network
itself. Split from fetch_gene_expression.py (retrieval) and
summarize_expression.py (text) on purpose: get data / describe it / draw
it, three tools. No caching: this fetches its own copy of the data every
time it's called.
"""

from __future__ import annotations

import altair as alt
import httpx
import pandas as pd

from . import ToolResult
from .fetch_gene_expression import get_dataframe
from .resolve_gene import GeneNotFoundError

# A gene's per-sample profile across all GTEx tissues is ~15-20k points (54
# tissues x up to ~800 samples each) - comfortably small to embed as-is, but
# past Altair's default 5000-row safety limit for inline datasets.
alt.data_transformers.disable_max_rows()

PSEUDOCOUNT = 0.01  # avoids log(0) on the log-scaled axis, for genes with ~zero expression
DEFAULT_COLOR = "#4c72b0"
HIGHLIGHT_COLOR = "#d62728"


def _profile_chart(df: pd.DataFrame, gene: str, highlight_tissue: str | None) -> alt.Chart:
    df = df.copy()
    df["tpm_adj"] = df["tpm"] + PSEUDOCOUNT
    # GTEx's tissue IDs are underscored (e.g. "Brain_Cortex") because that's
    # what the API takes as a parameter - but that's not how a human reads
    # an axis label, so display a spaced-out copy without touching the
    # field the tool's own highlight_tissue argument is matched against.
    df["tissue_label"] = df["tissue"].str.replace("_", " ", regex=False)
    df["highlighted"] = df["tissue"] == highlight_tissue if highlight_tissue else False

    tissue_order = (
        df.groupby("tissue_label")["tpm"].median().sort_values(ascending=False).index.tolist()
    )
    # Many samples floor out at exactly PSEUDOCOUNT (true zero expression),
    # so the data's own min/max would put points right at the domain edge -
    # half-clipped by the plot boundary since a log scale's default domain
    # is an exact fit. Pad it by a fixed log-space factor so nothing sits
    # flush against either edge.
    domain = [df["tpm_adj"].min() / 2, df["tpm_adj"].max() * 2]
    return (
        # Horizontal orientation: 54 tissue names read far more comfortably
        # down a y-axis than crammed and rotated along an x-axis.
        alt.Chart(df)
        .mark_boxplot(size=12, median={"color": "black", "strokeWidth": 1.5})
        .encode(
            y=alt.Y(
                "tissue_label:N",
                sort=tissue_order,
                title=None,
                axis=alt.Axis(labelFontSize=12),
            ),
            x=alt.X(
                "tpm_adj:Q",
                title="TPM + 0.01 (log scale)",
                scale=alt.Scale(type="log", domain=domain),
            ),
            color=alt.Color(
                "highlighted:N",
                scale=alt.Scale(domain=[False, True], range=[DEFAULT_COLOR, HIGHLIGHT_COLOR]),
                legend=None,
            ),
            tooltip=["tissue_label:N"],
        )
        .properties(
            width="container",
            height=alt.Step(20),  # fixed per-tissue row height - explicit "breathing room"
            title=f"{gene} expression across GTEx tissues (per-sample TPM)",
        )
    )


def plot_gene_expression(gene: str, highlight_tissue: str | None = None) -> ToolResult:
    """Chart a gene's per-sample expression distribution across every GTEx
    tissue, so you can see at a glance where it's tissue-specific vs.
    broadly expressed. Fetches the data itself. Optionally highlights one
    tissue in red, e.g. to call out the tissue summarize_expression found
    to be highest."""
    try:
        canonical_symbol, df, api_url = get_dataframe(gene)
    except GeneNotFoundError as exc:
        return ToolResult(text=f"error: {exc}")
    except httpx.HTTPError as exc:
        return ToolResult(text=f"error: could not reach GTEx ({exc})")

    chart = _profile_chart(df, canonical_symbol, highlight_tissue)
    highlight_note = f" (highlighting {highlight_tissue})" if highlight_tissue else ""
    return ToolResult(
        text=f"Rendered {canonical_symbol}'s expression chart across GTEx tissues{highlight_note}.",
        chart=chart.to_dict(),
        api_url=api_url,
        raw_data={
            "gene": canonical_symbol,
            "highlight_tissue": highlight_tissue,
            "tissue_count": int(df["tissue"].nunique()),
            "sample_count": len(df),
            "mark": "boxplot",
            "log_scale_axis": "x",
        },
    )
