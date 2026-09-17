"""Tool: fetch a gene's real per-sample expression across every GTEx tissue.

The data-acquisition step: pure retrieval, no interpretation. Resolving the
gene symbol (resolve_gene.py) and summarizing what came back
(summarize_expression.py) are deliberately separate tools - see those
modules' docstrings.

No caching, deliberately: every call really hits GTEx (~150-200ms for the
full 54-tissue pull), so the API URL shown in the chat is always real.
"""

from __future__ import annotations

import httpx
import pandas as pd

from . import ToolResult
from .resolve_gene import GeneNotFoundError, get_gencode_id

DATASET_ID = "gtex_v10"
GTEX_API = "https://gtexportal.org/api/v2"


def get_dataframe(gene: str) -> tuple[str, pd.DataFrame, str]:
    """Return (canonical_symbol, dataframe, api_url) for a gene, resolving
    it first."""
    gencode_id, canonical_symbol, _resolve_url, _record = get_gencode_id(gene)
    resp = httpx.get(
        f"{GTEX_API}/expression/geneExpression",
        params={"gencodeId": gencode_id, "datasetId": DATASET_ID, "itemsPerPage": 100},
        timeout=30,
    )
    resp.raise_for_status()
    entries = resp.json()["data"]
    df = pd.DataFrame(
        {"tissue": entry["tissueSiteDetailId"], "tpm": value}
        for entry in entries
        for value in entry["data"]
    )
    return canonical_symbol, df, str(resp.url)


def fetch_gene_expression(gene: str) -> ToolResult:
    """Fetch a gene's real per-sample expression across all ~54 GTEx
    tissues (resolving the gene symbol first). Pure data acquisition -
    pair with summarize_expression or plot_gene_expression to do something
    with what comes back."""
    try:
        canonical_symbol, df, api_url = get_dataframe(gene)
    except GeneNotFoundError as exc:
        return ToolResult(text=f"error: {exc}")
    except httpx.HTTPError as exc:
        return ToolResult(text=f"error: could not reach GTEx ({exc})")

    preview_rows = 10
    return ToolResult(
        text=(
            f"Fetched {len(df)} real per-sample TPM values for {canonical_symbol} "
            f"across {df['tissue'].nunique()} GTEx tissues."
        ),
        api_url=api_url,
        raw_data={
            "total_samples": len(df),
            "tissue_count": int(df["tissue"].nunique()),
            "preview": df.head(preview_rows).to_dict(orient="records"),
            "preview_note": f"showing {preview_rows} of {len(df)} rows",
        },
    )
