---
tool: resolve_gene
description: resolve a gene symbol (like 'BRCA1') to its stable GENCODE ID, the identifier GTEx actually indexes by
call: {"tool": "resolve_gene", "gene": "<gene symbol>"}
---

Step 1 of the pipeline. [agent.py](../agent.py) reads the `description` and
`call` fields above (between the `---` markers) at startup to build the
"Available tools" section of the system prompt.

The code lives in [tools/resolve_gene.py](../tools/resolve_gene.py). The
other tools (`fetch_gene_expression`, `summarize_expression`,
`plot_gene_expression`) will resolve the gene themselves if this step is
skipped - but calling it explicitly surfaces a real step that's usually
hidden: a gene symbol isn't a stable ID, and looking it up can fail (a
typo, a retired symbol) before you've spent a network call on the bigger
expression-data fetch.
