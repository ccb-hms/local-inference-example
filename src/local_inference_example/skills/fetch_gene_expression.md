---
tool: fetch_gene_expression
description: fetch a gene's real per-sample expression across every GTEx tissue (public data), after resolving it if needed
call: {"tool": "fetch_gene_expression", "gene": "<gene symbol>"}
---

Step 2 of the pipeline: pure data retrieval, no interpretation - see
`summarize_expression` and `plot_gene_expression` for what happens to the
data afterward.

The code lives in [tools/fetch_gene_expression.py](../tools/fetch_gene_expression.py).
It calls `resolve_gene`'s lookup itself, then pulls per-sample expression
across all ~54 tissues. No caching, on purpose: every call is a real API
request (both calls together take well under a second), so the API URL
shown in the chat is always the one that actually ran, not a stand-in for
a cached result.
