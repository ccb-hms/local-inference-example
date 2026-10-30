# Running a local chatbot with Ollama

[Ollama](https://ollama.com/) is a general-purpose local model server: once it's
running, *any* program on your machine can talk to it over an
OpenAI-compatible HTTP API. That's a different point on the spectrum from the
rest of this repo — see the diagram in the main
[README](../README.md#workshop-notes). The agent loop in
[agent.py](../src/local_inference_example/agent.py) is reachable only through
this app's own route and constrains the model's output to a fixed schema.
Ollama has no such constraint and no fixed route: it's a chatbot you can talk
to from a terminal, a script, or any OpenAI-client library, with nothing
hardcoded about GTEx or tool-calling.

This doc walks through installing Ollama, pulling a model, and talking to it
both from the command line and from a short Python script. See
[lm-studio.md](lm-studio.md) for the GUI-first alternative — the steps below
are nearly identical either way, since both speak the same OpenAI-compatible
API.

## Install

- **macOS**: download from [ollama.com/download](https://ollama.com/download),
  or `brew install ollama`.
- **Windows/Linux**: download from
  [ollama.com/download](https://ollama.com/download), or on Linux:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

Installing starts a background `ollama serve` process (on macOS/Windows it
runs as a menu-bar app) listening on `http://localhost:11434`. If it isn't
running, start it yourself:

```bash
ollama serve
```

## Pull a model

```bash
ollama pull phi3.5
```

This downloads the same family of model
([Phi-3.5-mini-instruct](https://huggingface.co/microsoft/Phi-3.5-mini-instruct))
that the rest of this repo runs by default, quantized for a laptop CPU/GPU.
Any model in the [Ollama library](https://ollama.com/library) works the same
way — swap `phi3.5` for `llama3.2`, `mistral`, `qwen2.5`, etc.

## Chat from the terminal

```bash
ollama run phi3.5
```

This drops you into an interactive chat, entirely local — no network call
beyond the initial download.

## Talk to it over the API

Ollama's server exposes an OpenAI-compatible `/v1/chat/completions` endpoint,
so anything that speaks that API can point at it with no code changes beyond
the base URL. A plain `curl` call:

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3.5",
    "messages": [{"role": "user", "content": "What is BRCA1?"}]
  }'
```

Or from Python, using [httpx](https://www.python-httpx.org/) (already a
dependency of this project — no `openai` package required):

```python
import httpx

response = httpx.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "phi3.5",
        "messages": [{"role": "user", "content": "What is BRCA1?"}],
    },
)
print(response.json()["choices"][0]["message"]["content"])
```

Because the model and the API are both running on your laptop, this works
offline once the model is pulled, and no prompt or response ever leaves your
machine.

## Multimodal: asking about an image, fully locally

Some Ollama models accept images alongside text, which matters whenever the
image itself is sensitive — a radiology image, for example, which is PHI
and generally shouldn't be sent to a hosted API at all. Pull a vision-capable
model:

```bash
ollama pull llama3.2-vision
```

Then send an image as a base64-encoded string alongside your question:

```python
import base64
import httpx

with open("scan.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = httpx.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "llama3.2-vision",
        "messages": [
            {
                "role": "user",
                "content": "What does this image show?",
                "images": [image_b64],
            }
        ],
        "stream": False,
    },
)
print(response.json()["message"]["content"])
```

(Ollama's native `/api/chat` endpoint takes images more simply than the
OpenAI-compatible route, which is why this example uses it instead.) The
image file never leaves your machine — the only thing happening is a local
HTTP request to `localhost`.

## Troubleshooting

- `curl: (7) Failed to connect` — Ollama isn't running; start it with
  `ollama serve` or open the app.
- Slow first response — the model is loading into memory; subsequent
  requests are faster as long as the model stays loaded.
- To free disk space, remove a model with `ollama rm phi3.5`.
