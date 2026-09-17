"""Tiny toolset the agent can call."""

from __future__ import annotations

import datetime
import math
from pathlib import Path

import altair as alt
import httpx
import pandas as pd
from scipy import stats

GTEX_API = "https://gtexportal.org/api/v2"
DATASET_ID = "gtex_v10"
OUTPUT_DIR = Path("output")
PSEUDOCOUNT = 0.01  # avoids log2(0)/log10(0) for genes with ~zero expression

# A small panel of well-known tissue-marker genes (plus two housekeeping
# genes as a "nothing to see here" control), pre-resolved to their GENCODE
# v39 IDs (matching the gtex_v10 dataset) so a volcano-plot call doesn't need
# a gene-lookup round trip per gene - just the expression fetch below.
MARKER_GENES: dict[str, str] = {
    "HBB": "ENSG00000244734.4",  # blood - hemoglobin
    "ALB": "ENSG00000163631.17",  # liver - albumin
    "SFTPC": "ENSG00000168484.13",  # lung - surfactant protein
    "MYH1": "ENSG00000109061.10",  # skeletal muscle - myosin heavy chain
    "GFAP": "ENSG00000131095.14",  # brain - astrocyte marker
    "SCGB2A2": "ENSG00000110484.7",  # breast - mammaglobin
    "MYH6": "ENSG00000197616.13",  # heart - myosin heavy chain
    "ADIPOQ": "ENSG00000181092.10",  # adipose - adiponectin
    "UMOD": "ENSG00000169344.16",  # kidney - uromodulin
    "INS": "ENSG00000254647.7",  # pancreas - insulin
    "ACTB": "ENSG00000075624.17",  # housekeeping control
    "GAPDH": "ENSG00000111640.15",  # housekeeping control
}


def _fetch_samples(tissue_a: str, tissue_b: str) -> list[dict]:
    resp = httpx.get(
        f"{GTEX_API}/expression/geneExpression",
        params={
            "gencodeId": list(MARKER_GENES.values()),
            "tissueSiteDetailId": [tissue_a, tissue_b],
            "datasetId": DATASET_ID,
            "itemsPerPage": 1000,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def log2fc_table(tissue_a: str, tissue_b: str) -> pd.DataFrame:
    """Fetch per-sample GTEx expression for the marker gene panel in two
    tissues and return a dataframe of log2 fold change + significance
    (Mann-Whitney U test on the raw per-sample TPM values) for each gene,
    tissue_b relative to tissue_a.
    """
    entries = _fetch_samples(tissue_a, tissue_b)
    by_gene: dict[str, dict[str, list[float]]] = {}
    for entry in entries:
        by_gene.setdefault(entry["geneSymbol"], {})[entry["tissueSiteDetailId"]] = entry["data"]

    rows = []
    for gene, by_tissue in by_gene.items():
        values_a, values_b = by_tissue.get(tissue_a), by_tissue.get(tissue_b)
        if not values_a or not values_b:
            continue
        mean_a = sum(values_a) / len(values_a)
        mean_b = sum(values_b) / len(values_b)
        log2fc = math.log2((mean_b + PSEUDOCOUNT) / (mean_a + PSEUDOCOUNT))
        _, p_value = stats.mannwhitneyu(values_a, values_b, alternative="two-sided")
        rows.append(
            {
                "gene": gene,
                f"mean_tpm_{tissue_a}": mean_a,
                f"mean_tpm_{tissue_b}": mean_b,
                "log2fc": log2fc,
                "p_value": p_value,
                "neg_log10_p": -math.log10(max(p_value, 1e-300)),
            }
        )
    return pd.DataFrame(rows).sort_values("log2fc").reset_index(drop=True)


def _volcano_chart(df: pd.DataFrame, tissue_a: str, tissue_b: str) -> alt.Chart:
    df = df.copy()
    df["significant"] = (df["p_value"] < 0.05) & (df["log2fc"].abs() > 1)
    return (
        alt.Chart(df)
        .mark_circle(size=120)
        .encode(
            x=alt.X("log2fc:Q", title=f"log2 fold change ({tissue_b} vs {tissue_a})"),
            y=alt.Y("neg_log10_p:Q", title="-log10(p-value)"),
            color=alt.Color(
                "significant:N",
                scale=alt.Scale(domain=[True, False], range=["#DD8452", "#4C72B0"]),
                legend=alt.Legend(title="|log2FC| > 1 and p < 0.05"),
            ),
            tooltip=["gene", "log2fc", "p_value"],
        )
        .properties(
            width=450,
            height=400,
            title=f"Marker-gene expression: {tissue_b} vs {tissue_a}",
        )
        .interactive()
    )


def volcano(tissue_a: str, tissue_b: str) -> str:
    """Compare a panel of tissue-marker genes between two GTEx tissues and
    save an interactive volcano plot (log2FC vs significance) so you can
    check the result against a picture, not just numbers."""
    try:
        df = log2fc_table(tissue_a, tissue_b)
    except httpx.HTTPError as exc:
        return f"error: could not fetch GTEx data ({exc})"

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"volcano_{tissue_a}_vs_{tissue_b}.html"
    _volcano_chart(df, tissue_a, tissue_b).save(path)

    top_up = df.iloc[-1]
    top_down = df.iloc[0]
    return (
        f"Compared {len(df)} marker genes between {tissue_a} and {tissue_b}. "
        f"Most enriched in {tissue_b}: {top_up['gene']} (log2FC={top_up['log2fc']:.2f}). "
        f"Most enriched in {tissue_a}: {top_down['gene']} (log2FC={top_down['log2fc']:.2f}). "
        f"Interactive volcano plot saved to {path}"
    )


def get_time() -> str:
    """Return the current local date and time."""
    return datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")


TOOLS = {
    "volcano": volcano,
    "get_time": get_time,
}
