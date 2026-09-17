---
tool: plot_gene_expression
description: chart a gene's expression distribution across every GTEx tissue (optionally highlighting one tissue in red), so you can see whether it's tissue-specific or broadly expressed
call: {"tool": "plot_gene_expression", "gene": "<gene symbol>", "highlight_tissue": "<optional tissue name, or omit>"}
---

Step 4 of the pipeline (the "draw the data" step) - a sibling of
`summarize_expression` (the "describe the data" step). Both fetch their own
copy of the data (see [fetch_gene_expression.md](fetch_gene_expression.md) -
no caching, so every call is a real API request).

`highlight_tissue` is optional: pass the tissue `summarize_expression`
found to be highest to call it out in red on the chart. It must be a real
GTEx tissue name - the JSON schema constrains it to the same list `resolve_gene`
and `fetch_gene_expression` implicitly search over.

The code lives in [tools/plot_gene_expression.py](../tools/plot_gene_expression.py).
