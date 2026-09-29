# Local Inference Example

This is a hands-on demo that downloads a small open-weight model from
Hugging Face, runs it entirely on your own laptop, and wraps it in a
minimal tool-using ("agentic") loop that calls a real public
bioinformatics API, with a browser UI so you can watch it work.

Running the model locally instead of calling a hosted API has a few
practical advantages here. After the first download the model itself
needs no internet connection, so it keeps working offline (only the
tools' calls to the public GTEx API need a connection). Your prompts and
the model's reasoning stay on your laptop, so there's no API key and no
request log sitting on someone else's server. Because the weights are
open, you can actually inspect every prompt, step, and tool call the
model produces, rather than treating it as a black box. And because
nothing here depends on a vendor's API, you can swap the model, edit a
tool's schema, or change the prompt directly. Running the model itself
also costs nothing beyond the electricity to run your laptop: there's no
per-token or per-request charge, no matter how many questions you ask.

It works on macOS and Windows/Linux, and runs on CPU only by default.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/)
(works the same on macOS and Windows).

```bash
git clone git@github.com:ccb-hms/local-inference-example.git
cd local-inference-example
uv sync
uv run local-inference-example
```

`uv run` downloads the model before it opens the browser (~3GB, cached
under `~/.cache/huggingface` for next time), with a progress bar so you can
watch how long it's got left. After that, http://127.0.0.1:8000 opens with
the model already loaded and ready to answer. Every question still needs
internet, since the tools query GTEx live.

## What it does

There's a chat panel on the left and a chart panel on the right. Ask about
a gene (e.g. *"where is BRCA1 expressed?"*) and the model, running
entirely on your laptop, decides which tools to call, in what order, to
answer you. Every
tool call and its result is narrated into the chat *as it actually
happens*, over a real streaming connection: you're watching the agent loop
run live, token by token.

![Demo: asking the local model a gene expression question and watching it call tools live, ending in a rendered chart](assets/demo.gif)

```mermaid
flowchart LR
    subgraph laptop["Your laptop (offline-capable)"]
        You["You type a question"] --> UI["Browser UI\n(plain HTML/JS, EventSource)"]
        UI -- "GET /api/chat/stream" --> Server["FastAPI server\n(Server-Sent Events)"]
        Server --> LLM["Qwen2.5-1.5B\n(local, CPU/MPS/GPU)"]
        LLM -- "JSON tool call\n(schema-constrained)" --> Loop["agent loop\n(a generator)"]
        Loop --> LLM
        LLM -- "final_answer" --> Server
        Loop -. "one SSE event\nper step, live" .-> UI
    end
    Loop <-- "gene symbol" --> GTEx["GTEx Portal API\n(public, no key)"]
    UI -- "vega-embed" --> Chart["rendered box plot,\nas soon as it's ready"]
```

`run_agent_stream` in [agent.py](src/local_inference_example/agent.py) is a
Python generator that `yield`s each step the instant it's produced;
[server.py](src/local_inference_example/server.py) turns that into a
Server-Sent Events response, and the browser's `EventSource` renders each
one as it arrives. The chart itself appears the moment
`plot_gene_expression` finishes, well before the whole run is done.

The model is [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct),
small enough to run on a laptop CPU with no GPU required.

## The pipeline is four atomic tools

A real gene-expression lookup is a chain of distinct steps, each of which
can be inspected (or fail) on its own. Each is its own file in
[tools/](src/local_inference_example/tools/), and each step is narrated
separately in the chat:

1. **`resolve_gene`**: a gene symbol like `BRCA1` isn't a stable ID; GTEx
   indexes by GENCODE ID. This step looks it up (and is where a typo or a
   made-up gene name fails, cleanly).
2. **`fetch_gene_expression`**: pure data acquisition, pulling real
   per-sample TPM values for that gene across all ~54 GTEx tissues.
3. **`summarize_expression`**: turns the fetched data into a plain-text
   summary (highest-expressing tissue, tissue-specificity ratio).
4. **`plot_gene_expression`**: turns the same fetched data into an
   interactive [Altair](https://altair-viz.github.io/) box plot showing the
   real per-sample distribution instead of a single median bar. Takes an
   optional `highlight_tissue` argument: ask something like *"where is INS
   expressed, highlight the pancreas"* and the model can call it out in red.

Each step resolves/fetches what it needs itself if the model calls them out
of order (or skips straight to `plot_gene_expression`), rather than failing.
There's no caching, on purpose: every call really hits GTEx (each takes well
under a second), so the API URL shown in the chat is always the real
request that ran. A fifth tool, `get_time`, exists purely to show that not
every tool call has to hit a public API.

```mermaid
flowchart TD
    Start(["User: 'where is BRCA1 expressed?'"]) --> Resolve["resolve_gene('BRCA1')"]
    Resolve -- "GENCODE ID" --> Fetch["fetch_gene_expression('BRCA1')"]
    Fetch -- "per-sample TPM" --> Summarize["summarize_expression('BRCA1')"]
    Fetch --> Plot["plot_gene_expression('BRCA1')"]
    Summarize --> Final(["final_answer"])
    Plot --> Final
    Resolve -. "gene not found" .-> Final
```

Every step, including the model's final answer, is narrated as a colored
chat bubble: yellow for the call itself, purple for the exact API URL it hit
(ellipsis-truncated, hover for the full thing), green for the data that came
back, blue for the answer. Click any bubble (or just watch as they appear)
and a panel below the chart shows exactly what that step really did: the
tool's actual Python source for a yellow bubble, the request broken into
method/endpoint/params for a purple one, the real JSON GTEx returned for a
green one, color-coded to match. Nothing here is simulated or summarized
after the fact: it's the same `ToolResult` object the agent loop used,
serialized straight into the stream.

## The model is only told what skills/*.md says

[agent.py](src/local_inference_example/agent.py) doesn't hardcode a
tool-description string. At startup it reads every file in
[skills/](src/local_inference_example/skills/), one markdown file per
tool, with a `tool` / `description` / `call` frontmatter block, and builds
the "Available tools" section of the system prompt from that. The code
(`tools/`) and what the model is told about it (`skills/`) are separate,
individually editable pieces, closer to how a real agent framework (MCP
tool descriptions, Claude Skills) separates them than a single hardcoded
prompt string would be. Edit a `skills/*.md` file and the model's
instructions change; no Python edit required.

Every JSON object the model emits is additionally constrained by
[outlines](https://github.com/dottxt-ai/outlines) to match a
[pydantic](https://docs.pydantic.dev/) schema (`AgentStep` in
[agent.py](src/local_inference_example/agent.py)), so it's guaranteed to
be a syntactically well-formed tool call or final answer, no regex-parsing
of free-form text required. It can still pick the *wrong* tool, or waste a
step on `get_time`. The schema only guarantees the call is syntactically
valid; it says nothing about whether calling it was the right call.

## Swapping in a different model

```bash
uv run local-inference-example --model-size 0.5b   # ~1GB, faster, less reliable
uv run local-inference-example --model-size 1.5b    # default
```

`Qwen/Qwen2.5-0.5B-Instruct` still produces syntactically valid tool calls
(that's what the JSON schema constraint guarantees), but noticeably more
often skips a step or loops instead of giving a final answer, a good
illustration of the difference between constraining a model's *syntax*
versus its *judgment*. For any other model, change `MODEL_SIZES` in
[model.py](src/local_inference_example/model.py), or pass `--model` (see
below) to try one without editing code.

### Finding a model that fits your hardware

```bash
uv run python scripts/find_hardware_model.py
uv run python scripts/find_hardware_model.py --use-case coding --limit 10
```

[scripts/find_hardware_model.py](scripts/find_hardware_model.py) runs
[llmfit](https://github.com/AlexsJones/llmfit) (via `uvx`, so nothing extra
needs installing) to detect your CPU, RAM, and GPU/VRAM, and prints the
models it scores highest for that hardware, each linked to its Hugging Face
page. Try one directly, no code changes:

```bash
uv run local-inference-example --model Qwen/Qwen2.5-3B-Instruct
```

Only dense, full-precision instruct models work here: `model.py` loads
weights with `transformers`' `AutoModelForCausalLM`, so quantized GGUF/MLX/
AWQ/EXL2 builds - the formats llmfit recommends for runtimes like llama.cpp
or MLX - won't load. Stick to a model's plain `-Instruct` repo, not a
quantized variant of it.

## Freeing disk space

The downloaded weights (~1-3GB per size) sit in your shared Hugging Face
cache under `~/.cache/huggingface`. To delete just the models this project
downloaded, without touching any other cached models:

```bash
uv run python scripts/clean_models.py
```

## Workshop notes

This is deliberately minimal: one small model, five tools, no agent
framework, no database. The point is to show what an "agent loop" actually
is under the hood: a prompt built from markdown files, a JSON schema, and
a `while` loop, before reaching for something like LangChain or an MCP
server.

A few things worth calling out live:

- The `AgentStep` schema guarantees the model's output always parses as
  valid JSON, but it doesn't guarantee the model calls the tools in a
  sensible order or stops once it has enough information. See
  [agent.py](src/local_inference_example/agent.py)'s stall-detection
  fallback, which exists because even Qwen2.5-1.5B occasionally re-issues
  the same tool call instead of answering. This is the difference between
  constraining a model's syntax and constraining its judgment.
- `MAX_STEPS` in [agent.py](src/local_inference_example/agent.py) caps how
  many tool calls one query can trigger, and it's a real safety mechanism:
  without it, a confused small model can loop indefinitely. Splitting one
  tool into four raised the minimum number of steps a correct answer
  needs, so `MAX_STEPS` had to grow along with it.
- The LLM runs entirely on your machine, and the only network calls it
  triggers are the tools' requests to the public GTEx API. Those requests
  only ever carry a gene symbol; no personal data and no query text leave
  your laptop.
- The gene symbol, tissue names, and TPM values in each Observation come
  straight from GTEx, but it's worth checking the model's own commentary
  against that data rather than taking it at face value. Ask it to "pick
  a gene associated with Alzheimer's" and it may confidently name one
  that isn't correct, because there's no search-by-disease tool and that
  step is unconstrained model guesswork. The schema only constrains the
  shape of a tool call; it says nothing about the judgment behind picking
  `gene='ALDH7A1'` over the real Alzheimer's genes (`APOE`, `APP`,
  `PSEN1`/`PSEN2`, `TREM2`). It's worth pairing every number the model
  reports with the chart instead of trusting its prose alone, and worth
  asking a workshop audience which parts of an answer they'd trust and
  which they'd check.

## Why not just use the model's native tool-calling format?

The obvious starting point for tool use is Qwen2.5-Instruct's own
tool-calling convention: pass `tools=` to `tokenizer.apply_chat_template`,
and the model free-generates a
`<tool_call>{"name": ..., "arguments": {...}}</tool_call>` block, which you
parse yourself (`src/local_inference_example/native_model.py` prototypes
exactly this). That block is JSON, but "the model output JSON" is a
weaker guarantee than "the model output JSON matching the schema our
tools need." Nothing about the chat template stops it from naming a tool
that doesn't exist, dropping a required argument, or emitting a tissue
name that isn't a real GTEx tissue. That gap is what you have to close.

One way to close it is to parse the JSON, validate it against the same
pydantic `AgentStep` schema, and retry (feeding the error back to the
model) whenever it fails. That works, but every retry is a full extra
generation: each failure costs real latency, and you're still only
lowering the failure probability rather than eliminating it.

`model.py` takes the other approach and constrains decoding itself, using
[outlines](https://github.com/dottxt-ai/outlines) to compile the
`AgentStep` schema into a finite-state machine that restricts which
*tokens* the model is allowed to sample at each step. The output can't
help but be schema-valid, so there's no invalid JSON to catch and nothing
to retry.

We measured the actual difference (`scripts/compare_failure_rates.py`):
how often raw output validates against `AgentStep` on the *first try*, no
retries, 8 samples per query:

| Model | native `<tool_call>` + pydantic | outlines (constrained decoding) |
|---|---|---|
| Qwen2.5-1.5B-Instruct (default) | 32/32 (100%) | 32/32 (100%) |
| Qwen2.5-0.5B-Instruct | 24/32 (75%) | 32/32 (100%) |

At the default 1.5B size, validate-and-retry would rarely even need to
retry. At 0.5B, every native failure was the same shape: for a
zero-argument tool (`get_time`), the model emitted `{"name": "get_time"}`
and omitted the required `"arguments"` key entirely, instead of the
`"arguments": {}` the Hermes spec (and our validator) requires. Outlines
can't produce that failure: the finite-state machine makes an
empty-but-present `arguments` object structurally unavoidable, regardless
of model size.

That specific 0.5B failure turned out to be promptable away: adding one
sentence to the system prompt ("every tool call must include an
`arguments` object, even for a tool with no parameters") took native's
0.5B score from 24/32 back to 32/32. That's the real tradeoff.
Validate-and-retry *can* get you the same reliability, but only after
you've discovered the failure mode empirically, by shipping it or by
running exactly this kind of eval, and patched the prompt for it, and
you're still paying for retries on whatever failure mode you *haven't*
found yet. Outlines rules the whole category out by construction, before
you've even written a single test case. That's what "guarantees valid
syntax regardless of model size" (see the note above `DEFAULT_MODEL` in
[model.py](src/local_inference_example/model.py)) is actually buying you.
