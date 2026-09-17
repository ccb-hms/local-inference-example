---
tool: summarize_expression
description: summarize where a gene is most highly expressed and how tissue-specific it is, as plain numbers
call: {"tool": "summarize_expression", "gene": "<gene symbol>"}
---

Step 3 of the pipeline (the "describe the data" step) - a sibling of
`plot_gene_expression` (the "draw the data" step). Both fetch their own
copy of the data (see [fetch_gene_expression.md](fetch_gene_expression.md) -
no caching, so every call is a real API request).

The code lives in [tools/summarize_expression.py](../tools/summarize_expression.py).
