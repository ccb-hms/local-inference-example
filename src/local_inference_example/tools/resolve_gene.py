"""Tool: resolve a gene symbol to its stable GENCODE ID.

The first atomic step of the pipeline. Most genomic APIs and files don't
index by the gene symbol you'd type ("BRCA1") - they use a stable ID like
"ENSG00000012048.23" instead, because symbols get renamed and reused across
species and annotation releases. Making this its own tool call (rather than
folding it silently into the fetch step) surfaces that real step instead of
hiding it.

No caching, deliberately: every call really hits GTEx, so the API URL shown
in the chat is always real, not "would have been this, but we reused an
earlier result." The lookup is fast (~150ms) so there's no performance
reason to cache for a demo like this.
"""

from __future__ import annotations

import httpx

from . import ToolResult

GTEX_API = "https://gtexportal.org/api/v2"
GENCODE_VERSION = "v39"  # matches DATASET_ID in fetch_gene_expression.py


class GeneNotFoundError(Exception):
    pass


def get_gencode_id(gene: str) -> tuple[str, str, str, dict]:
    """Return (gencodeId, canonical_symbol, api_url, raw_record) for a gene."""
    resp = httpx.get(
        f"{GTEX_API}/reference/geneSearch",
        params={"geneId": gene, "gencodeVersion": GENCODE_VERSION},
        timeout=10,
    )
    resp.raise_for_status()
    matches = resp.json()["data"]
    if not matches:
        raise GeneNotFoundError(f"'{gene}' doesn't match any gene symbol in GTEx")
    # Prefer an exact, protein-coding match over e.g. a same-prefixed pseudogene.
    exact = [
        m for m in matches
        if m["geneSymbolUpper"] == gene.upper() and m["geneType"] == "protein coding"
    ]
    best = (exact or matches)[0]
    return best["gencodeId"], best["geneSymbol"], str(resp.url), best


def resolve_gene(gene: str) -> ToolResult:
    """Resolve a gene symbol (e.g. 'BRCA1') to its stable GENCODE ID - the
    identifier the rest of the pipeline actually queries GTEx with."""
    try:
        gencode_id, canonical_symbol, api_url, record = get_gencode_id(gene)
    except GeneNotFoundError as exc:
        return ToolResult(text=f"error: {exc}")
    except httpx.HTTPError as exc:
        return ToolResult(text=f"error: could not reach GTEx ({exc})")

    return ToolResult(
        text=f"Resolved '{gene}' to GENCODE ID {gencode_id} (canonical symbol: {canonical_symbol}).",
        api_url=api_url,
        raw_data=record,
    )
