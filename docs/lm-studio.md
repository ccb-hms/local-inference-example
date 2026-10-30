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

This doc walks through downloading a vision-capable model and uploading an
image to LM Studio's chat UI. See [ollama.md](ollama.md) for the equivalent
walkthrough in Ollama — the steps are nearly identical either way.

## Install

Download the installer for macOS, Windows, or Linux from
[lmstudio.ai/download](https://lmstudio.ai/download), and run it.

## Pick a vision-capable model — and mind the cloud ones

Not every model LM Studio offers can look at an image, and not every model
LM Studio offers runs on your laptop.

1. Open LM Studio and go to the **Discover** tab (the search/magnifying-glass
   icon in the left sidebar).
2. Search for a vision/multimodal model — `Qwen2-VL`, `LLaVA`, or `Gemma 3`
   all work. Vision-capable models are marked with a **Vision** capability
   badge in the search results; a plain text model (like
   `Phi-3.5-mini-instruct`) won't show that badge, and won't accept images
   later no matter what you do.
3. Pick a `.gguf` (or MLX, on Apple Silicon) build sized for your hardware —
   LM Studio flags ones that fit your RAM/VRAM in green — and click
   **Download**. If the model needs a separate vision adapter file, LM
   Studio downloads it for you automatically.

**Gotcha:** LM Studio also offers **cloud** models, run on LM Studio's own
servers rather than your laptop. These require you to sign in to an LM
Studio account and set up billing, and each message draws down paid
credits. The model picker separates **Local**, **Cloud**, and **Remote**
(another device on your network) models — if the point is keeping data on
your laptop, which it is for anything sensitive, stick to **Local** models
only and don't sign in to a cloud account you don't intend to use.

## Load the model

Click the chat-bubble icon in the left sidebar (**Chat**), then open the
model selector and choose your downloaded vision model to load it as the
active model for the conversation.

## Upload an image

With the vision model loaded:

1. Click the attach icon next to the message box (or drag the image file
   straight into the chat window — both work).
2. Select the image file from your laptop.
3. Type your question — e.g. *"What does this image show?"*
4. Send the message.

The image thumbnail appears in the chat alongside your message, and the
model's answer streams in below it, the same as a text-only reply.

## Why this matters for sensitive images

As long as the model you loaded is a Local one, the image is read from
disk, passed to the model in memory on your machine, and never uploaded
anywhere. That matters whenever the image itself is sensitive — a radiology
scan, for example, which is PHI and generally shouldn't be sent to a hosted
chatbot at all. Once the model is downloaded, this works with no internet
connection. A Cloud model defeats this entirely, since the image is sent to
LM Studio's servers to run.

## Troubleshooting

- No attach icon in the message box, or the model ignores the image — the
  loaded model is text-only; load a model with the **Vision** badge instead
  (see above).
- The model dropdown is empty — you haven't downloaded a model yet; go back
  to **Discover**.
- Slow first response after uploading an image — the model is loading into
  memory; it's faster on the next message as long as it stays loaded.
- To free disk space, remove a model from the **My Models** tab.
- To be certain you'll never accidentally run a (paid) cloud model, don't
  sign in to an LM Studio account, and check that the model picker shows
  your chosen model under **Local**, not **Cloud**.
