# local-inference-example

A short, hands-on demo for the CCB "APIs and Local Inference" workshop
([AI-45](https://ccb-hms.atlassian.net/browse/AI-45)): download a small
open-weight model from Hugging Face, run inference entirely on your own
laptop (no API key, no internet needed after the first download), and wrap
it in a minimal tool-using ("agentic") loop.

Works on macOS and Windows/Linux, CPU-only by default.

## What it does

The model is [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
(~3GB download), small enough to run on a laptop CPU with no GPU required.
It's wrapped in a tiny tool-calling loop ([agent.py](src/local_inference_example/agent.py))
that lets the model call two example tools ([tools.py](src/local_inference_example/tools.py)):

- `calculator(expression)` - arithmetic the model shouldn't be trusted to do itself
- `get_time()` - real-world state the model can't know on its own

Each step the model produces is constrained by
[outlines](https://github.com/dottxt-ai/outlines) to be valid JSON matching a
[pydantic](https://docs.pydantic.dev/) schema ([agent.py](src/local_inference_example/agent.py):`AgentStep`) -
so it's guaranteed to be a syntactically well-formed tool call or final
answer, no regex parsing of free-form text required. The model can still
choose the wrong tool; it just can't return malformed JSON.

Ask it something like `what's 17 * 23, plus 4?` and watch it call the
calculator tool instead of guessing.

## Setup

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/)
(works the same on macOS and Windows).

```bash
git clone git@github.com:ccb-hms/local-inference-example.git
cd local-inference-example
uv sync
```

## Run

```bash
uv run local-inference-example
```

The first run downloads the model from Hugging Face (~3GB) and caches it
under `~/.cache/huggingface`; later runs start instantly offline.

## Swapping in a different model

Change `DEFAULT_MODEL` in [model.py](src/local_inference_example/model.py) to
any small instruct model on the Hugging Face Hub. Worth trying live in a
workshop: dropping to `Qwen/Qwen2.5-0.5B-Instruct` (~1GB) still produces
syntactically valid tool calls (that's what the JSON schema constraint
guarantees), but noticeably more often picks the wrong tool or loops instead
of giving a final answer - a good illustration of the difference between
constraining a model's *syntax* versus its *judgment*.

## Workshop notes

This is deliberately minimal: one small model, two toy tools, no agent
framework. The point is to show what an "agent loop" actually is under the
hood - a prompt, a JSON schema, and a `while` loop - before reaching for
something like LangChain or an MCP server.

Two things worth calling out live:

- **Constrained decoding vs. model judgment.** The `AgentStep` schema
  guarantees the model's output always parses as valid JSON. It does not
  guarantee the model picks the *right* tool - see [agent.py](src/local_inference_example/agent.py)'s
  stall-detection fallback, which exists because even Qwen2.5-1.5B
  occasionally re-issues the same tool call instead of answering.
- **Step limits are a real safety mechanism, not boilerplate.** `MAX_STEPS`
  in [agent.py](src/local_inference_example/agent.py) caps how many tool
  calls one query can trigger - without it, a confused small model can loop
  indefinitely.
