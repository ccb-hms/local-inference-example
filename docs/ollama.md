# Running a local chatbot with Ollama

[Ollama](https://ollama.com/) is a general-purpose local chatbot app: once
it's running, you get a chat window on your own laptop with no setup beyond
picking a model. That's a different point on the spectrum from the rest of
this repo — see the diagram in the main
[README](../README.md#workshop-notes). The agent loop in
[agent.py](../src/local_inference_example/agent.py) only answers questions
about gene expression, through this app's own browser UI. Ollama's chat
window is a general-purpose chatbot: ask it anything, and — if you pick a
vision-capable model — show it an image.

This doc walks through downloading a vision-capable model and uploading an
image to Ollama's chat UI. See [lm-studio.md](lm-studio.md) for the
equivalent walkthrough in LM Studio — the steps are nearly identical either
way.

## Install

- **macOS**: download from [ollama.com/download](https://ollama.com/download),
  or `brew install ollama`.
- **Windows/Linux**: download the installer from
  [ollama.com/download](https://ollama.com/download).

Launch the app once installed. On macOS/Windows it adds an icon to the menu
bar/system tray; click it to open the chat window.

## Pick a vision-capable model — and avoid the cloud ones

Not every model Ollama offers can look at an image, and not every model
Ollama offers runs on your laptop.

Browse [ollama.com/search](https://ollama.com/search) and filter by the
**vision** capability tag to see which models can accept images at all —
plain text models like `phi3.5` or `llama3.2` won't show an image-upload
option no matter what you do. A few local vision models worth trying:
`llama3.2-vision`, `llava`, `qwen2.5vl`, `gemma3`.

**Gotcha:** Ollama's catalog also lists *cloud* models — run on Ollama's
servers, not your machine, requiring an Ollama account, an internet
connection, and (for most of them) paid credits. In the model list these are
tagged **cloud** and carry a `:cloud` suffix on their name (e.g.
`gpt-oss:120b-cloud`), often shown with a `$` price marker. If the point is
keeping data on your laptop — which it is, for anything sensitive — skip
every model tagged **cloud** or suffixed `:cloud`, even if its name
otherwise looks like what you want. Stick to plain tags with no `:cloud`
suffix, such as `llama3.2-vision` or `llama3.2-vision:11b`.

## Download and load the model

- From the chat window, open the model selector and type the model's name
  (e.g. `llama3.2-vision`). If it isn't downloaded yet, selecting it starts
  the download (a few GB; only needed once).
- Or pull it ahead of time from a terminal:
  ```bash
  ollama pull llama3.2-vision
  ```
  Models pulled this way show up in the chat window's model selector too.

Once downloaded, select it in the chat window so it's the active model for
your conversation.

## Upload an image

With a vision-capable (non-cloud) model selected:

1. Drag the image file straight into the chat window, or use the chat
   window's attach/add-file control if one is shown — both add the image to
   your next message.
2. Type your question — e.g. *"What does this image show?"*
3. Send the message.

The image thumbnail appears in the chat alongside your message, and the
model's answer streams in below it, the same as a text-only reply.

## Why this matters for sensitive images

As long as the model you picked is a local one (no `:cloud` suffix), the
image is read from disk, passed to the model in memory on your machine, and
never uploaded anywhere. That matters whenever the image itself is sensitive
— a radiology scan, for example, which is PHI and generally shouldn't be
sent to a hosted chatbot at all. Once the model is downloaded, this works
with no internet connection. A cloud model defeats this entirely, since the
image is sent to Ollama's servers to run.

## Troubleshooting

- No way to attach an image, or the model ignores it — the selected model
  is text-only; switch to a vision-capable model (see above).
- Nothing happens when you click the menu bar icon — Ollama's background
  service may not be running; reopen the app, or run `ollama serve` in a
  terminal.
- Slow first response after uploading an image — the model is loading into
  memory; it's faster on the next message as long as it stays loaded.
- To free disk space, remove a model from the chat window's manage-models
  view, or run `ollama rm <model>` in a terminal.
- To be certain you'll never accidentally run a cloud model, disable cloud
  features entirely: set `OLLAMA_NO_CLOUD=1` in your environment (or
  `"disable_ollama_cloud": true` in `~/.ollama/server.json`) and restart
  Ollama.
