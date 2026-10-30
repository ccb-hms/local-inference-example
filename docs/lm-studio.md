# Running a local chatbot with LM Studio

[LM Studio](https://lmstudio.ai/) is a general-purpose local model server with
a desktop GUI: once its server is running, *any* program on your machine can
talk to it over an OpenAI-compatible HTTP API. That's a different point on
the spectrum from the rest of this repo — see the diagram in the main
[README](../README.md#workshop-notes). The agent loop in
[agent.py](../src/local_inference_example/agent.py) is reachable only through
this app's own route and constrains the model's output to a fixed schema. LM
Studio has no such constraint and no fixed route: it's a chatbot you can talk
to from the GUI, a terminal, or any OpenAI-client library, with nothing
hardcoded about GTEx or tool-calling.

This doc walks through installing LM Studio, downloading a model, and
talking to it both from the GUI and from a short Python script. See
[ollama.md](ollama.md) for the CLI-first alternative — the steps below are
nearly identical either way, since both speak the same OpenAI-compatible API.

## Install

Download the installer for macOS, Windows, or Linux from
[lmstudio.ai/download](https://lmstudio.ai/download).

## Download a model

Open LM Studio, click the search icon in the left sidebar, and search for a
model — for example `Phi-3.5-mini-instruct`, the same model the rest of this
repo runs by default. Pick a quantized `.gguf` build sized for your hardware
(LM Studio flags ones that fit your RAM/VRAM in green) and click **Download**.

## Chat from the GUI

Click the chat icon in the left sidebar, select the downloaded model from the
dropdown at the top, and start typing — entirely local, no network call
beyond the initial download.

## Start the local server

Click the developer/server icon in the left sidebar (`</>`), select a loaded
model, and click **Start Server**. By default it listens on
`http://localhost:1234`.

## Talk to it over the API

LM Studio's server exposes an OpenAI-compatible `/v1/chat/completions`
endpoint, so anything that speaks that API can point at it with no code
changes beyond the base URL. A plain `curl` call:

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi-3.5-mini-instruct",
    "messages": [{"role": "user", "content": "What is BRCA1?"}]
  }'
```

(The `model` field just needs to match whatever's loaded in LM Studio; check
the exact name shown in the server tab.)

Or from Python, using [httpx](https://www.python-httpx.org/) (already a
dependency of this project — no `openai` package required):

```python
import httpx

response = httpx.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "phi-3.5-mini-instruct",
        "messages": [{"role": "user", "content": "What is BRCA1?"}],
    },
)
print(response.json()["choices"][0]["message"]["content"])
```

Because the model and the API are both running on your laptop, this works
offline once the model is downloaded, and no prompt or response ever leaves
your machine.

## Multimodal: asking about an image, fully locally

Some models in LM Studio's catalog accept images alongside text, which
matters whenever the image itself is sensitive — a radiology image, for
example, which is PHI and generally shouldn't be sent to a hosted API at
all. Search for and download a vision-capable model, such as
`Qwen2-VL` or `llava`, then load it the same way as above.

The OpenAI-compatible endpoint accepts images as base64 data URIs, the same
format the hosted OpenAI vision API uses:

```python
import base64
import httpx

with open("scan.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = httpx.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "qwen2-vl",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What does this image show?"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
    },
)
print(response.json()["choices"][0]["message"]["content"])
```

The image file never leaves your machine — the only thing happening is a
local HTTP request to `localhost`.

## Troubleshooting

- `curl: (7) Failed to connect` — the server tab shows "Stopped"; click
  **Start Server** in LM Studio.
- Slow first response — the model is loading into memory; subsequent
  requests are faster as long as the model stays loaded.
- To free disk space, remove a model from the **My Models** tab in LM Studio.
