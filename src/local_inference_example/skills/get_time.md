---
tool: get_time
description: get the current local date and time
call: {"tool": "get_time"}
---

A deliberately trivial second tool: it calls no external API, just
[tools/get_time.py](../tools/get_time.py)'s system clock. It exists to make
the point that a tool call is just a function call the model asks for - not
every tool needs to hit a public API like `gene_tissue_profile` does.
