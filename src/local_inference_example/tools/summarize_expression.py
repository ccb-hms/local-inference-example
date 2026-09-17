"""Tool: summarize a gene's expression data as text.

The interpretation step, split from fetch_gene_expression.py's raw
retrieval and kept separate from plot_gene_expression.py's chart - three
different jobs (get data / describe it / draw it), three tools. No
caching: this fetches its own copy of the data every time it's called.
"""

from __future__ import annotations

import httpx

from . import ToolResult
from .fetch_gene_expression import get_dataframe
from .resolve_gene import GeneNotFoundError

PSEUDOCOUNT = 0.01  # avoids div-by-zero for the tissue-specificity ratio below


def summarize_expression(gene: str) -> ToolResult:
    """Summarize where a gene is most highly expressed across GTEx tissues
    and how tissue-specific it is, in plain numbers (fetching the data
    itself)."""
    try:
        canonical_symbol, df, api_url = get_dataframe(gene)
    except GeneNotFoundError as exc:
        return ToolResult(text=f"error: {exc}")
    except httpx.HTTPError as exc:
        return ToolResult(text=f"error: could not reach GTEx ({exc})")

    medians = df.groupby("tissue")["tpm"].median().sort_values(ascending=False)
    top_tissue, top_median = medians.index[0], medians.iloc[0]
    overall_median = medians.median()
    specificity = (top_median + PSEUDOCOUNT) / (overall_median + PSEUDOCOUNT)

    text = (
        f"{canonical_symbol}: highest median expression in {top_tissue} "
        f"({top_median:.2f} TPM), {specificity:.1f}x the median across all "
        f"{len(medians)} tissues."
    )
    return ToolResult(
        text=text,
        api_url=api_url,
        raw_data={
            "gene": canonical_symbol,
            "top_tissue": top_tissue,
            "top_tissue_median_tpm": round(float(top_median), 4),
            "cross_tissue_median_tpm": round(float(overall_median), 4),
            "specificity_ratio": round(float(specificity), 2),
            "tissue_count": len(medians),
            "median_tpm_by_tissue": {k: round(float(v), 4) for k, v in medians.items()},
        },
    )
