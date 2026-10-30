# Running a local chatbot with LM Studio

[LM Studio](https://lmstudio.ai/) is a general-purpose local chatbot app:
once it's running, you get a chat window on your own laptop with no setup
beyond picking a model. That's a different point on the spectrum from the
rest of this repo — see the diagram in the main
[README](../README.md#workshop-notes). The agent loop in
[agent.py](../src/local_inference_example/agent.py) only answers questions
about gene expression, through this app's own browser UI. LM Studio's chat
window is a general-purpose chatbot: ask it anything, and — if you pick a
vision-capable model — show it an image.

This doc walks through opening LM Studio's chat UI and uploading an image to
it. See [ollama.md](ollama.md) for the equivalent walkthrough in Ollama — the
steps are nearly identical either way.

## Install

Download the installer for macOS, Windows, or Linux from
[lmstudio.ai/download](https://lmstudio.ai/download), and run it.

## Download a vision-capable model

1. Open LM Studio and click the search/magnifying-glass icon in the left
   sidebar (**Discover**).
2. Search for a vision/multimodal model — `Qwen2-VL`, `LLaVA`, or `Gemma 3`
   all work. A plain text model (like `Phi-3.5-mini-instruct`) won't show an
   image-upload option later, so the model choice matters here.
3. Pick a `.gguf` build sized for your hardware — LM Studio flags ones that
   fit your RAM/VRAM in green — and click **Download**.

## Open the chat window

Click the chat-bubble icon in the left sidebar (**Chat**), then select your
downloaded vision model from the dropdown at the top of the window to load
it.

## Upload an image

With the vision model loaded:

1. Click the **+** (attach) icon next to the message box (or just drag the
   image file straight into the chat window — both work).
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

- No attach icon in the message box — the loaded model is text-only; load a
  vision-capable model instead (see above).
- The model dropdown is empty — you haven't downloaded a model yet; go back
  to **Discover**.
- Slow first response after uploading an image — the model is loading into
  memory; it's faster on the next message as long as it stays loaded.
- To free disk space, remove a model from the **My Models** tab.
