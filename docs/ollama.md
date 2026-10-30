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

This doc walks through opening Ollama's chat UI and uploading an image to it.
See [lm-studio.md](lm-studio.md) for the equivalent walkthrough in LM Studio
— the steps are nearly identical either way.

## Install

- **macOS**: download from [ollama.com/download](https://ollama.com/download),
  or `brew install ollama`.
- **Windows/Linux**: download the installer from
  [ollama.com/download](https://ollama.com/download).

## Open the chat window

Launch the Ollama app. On macOS/Windows it adds an icon to the menu
bar/system tray; click it and choose **New chat** (or **Open Ollama**) to
bring up the chat window. On Linux, or if no window appears, run
`ollama app` from a terminal, or just use `ollama run <model>` in the
terminal as a text-only fallback.

## Pick a vision-capable model

At the top of the chat window there's a model picker. Click it and search
for a vision/multimodal model — `llama3.2-vision`, `llava`, or `gemma3` all
work. If it's not downloaded yet, selecting it will prompt Ollama to pull it
first (a few GB; only needed once). A plain text model like `phi3.5` or
`llama3.2` won't show an image-upload option, so the model choice matters
here.

## Upload an image

With a vision-capable model selected:

1. Click the **+** or paperclip icon next to the message box (or just drag
   the image file straight into the chat window — both work).
2. Select the image file from your laptop.
3. Type your question in the message box — e.g. *"What does this image
   show?"*
4. Press Enter (or click send).

The image thumbnail appears in the chat alongside your message, and the
model's answer streams in below it, the same as a text-only reply.

## Why this matters for sensitive images

Everything above happens entirely on your laptop: the image is read from
disk, passed to the model in memory, and never uploaded anywhere. That
matters whenever the image itself is sensitive — a radiology scan, for
example, which is PHI and generally shouldn't be sent to a hosted chatbot at
all. Once the model is downloaded, this works with no internet connection.

## Troubleshooting

- No attach/paperclip icon in the chat box — the selected model is
  text-only; switch to a vision-capable model (see above).
- Nothing happens when you click the menu bar icon — Ollama's background
  service may not be running; reopen the app, or run `ollama serve` in a
  terminal.
- Slow first response after uploading an image — the model is loading into
  memory; it's faster on the next message as long as it stays loaded.
- To free disk space, remove a model from the model picker's manage-models
  view, or run `ollama rm <model>` in a terminal.
