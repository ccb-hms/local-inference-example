# Asking a local chatbot about an image

[Ollama](https://ollama.com/) and [LM Studio](https://lmstudio.ai/) are
general-purpose local chatbot apps: once one is running, you get a chat
window on your own laptop with no setup beyond picking a model. That's a
different point on the spectrum from the rest of this repo — see the
diagram in the main [README](../README.md#workshop-notes). The agent loop in
[agent.py](../src/local_inference_example/agent.py) only answers questions
about gene expression, through this app's own browser UI. These chat
windows are general-purpose chatbots: ask one anything, and — if you pick a
vision-capable model — show it an image.

That matters whenever the image itself is sensitive — a radiology scan, for
example, which is PHI and generally shouldn't be sent to a hosted chatbot at
all. As long as the model you pick is a *local* one, the image is read from
disk, passed to the model in memory on your machine, and never uploaded
anywhere; once the model is downloaded, this works with no internet
connection at all.

Ollama and LM Studio are interchangeable for this — pick whichever you
already have, or whichever installs more easily on your machine. The steps
below are nearly identical for both.

## Install

- **Ollama**: download from [ollama.com/download](https://ollama.com/download)
  (macOS also supports `brew install ollama`), and launch the app. On
  macOS/Windows it adds an icon to the menu bar/system tray; click it to open
  the chat window.
- **LM Studio**: download the installer for macOS, Windows, or Linux from
  [lmstudio.ai/download](https://lmstudio.ai/download), and run it.

## Pick a vision-capable model — and avoid the cloud ones

Not every model either app offers can look at an image, and not every model
either app offers runs on your laptop.

### Ollama

Browse [ollama.com/search](https://ollama.com/search) and filter by the
**vision** capability tag to see which models can accept images at all —
plain text models like `phi3.5` or `llama3.2` won't show an image-upload
option no matter what you do. A few local vision models worth trying:
`llama3.2-vision`, `llava`, `qwen2.5vl`, `gemma3`.

**Gotcha:** Ollama's catalog also lists *cloud* models — run on Ollama's
servers, not your machine, requiring an Ollama account, an internet
connection, and (for most of them) paid credits. In the model list these are
tagged **cloud** and carry a `:cloud` suffix on their name (e.g.
`gpt-oss:120b-cloud`), often shown with a `$` price marker. Skip every model
tagged **cloud** or suffixed `:cloud` — even if its name otherwise looks
like what you want — and stick to plain tags with no suffix, such as
`llama3.2-vision` or `llama3.2-vision:11b`.

From the chat window, open the model selector and type the model's name. If
it isn't downloaded yet, selecting it starts the download (a few GB; only
needed once). You can also pull it ahead of time from a terminal:

```bash
ollama pull llama3.2-vision
```

Models pulled this way show up in the chat window's model selector too.

### LM Studio

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
(another device on your network) models — stick to **Local** models only,
and don't sign in to a cloud account you don't intend to use.

Click the chat-bubble icon in the left sidebar (**Chat**), then open the
model selector and choose your downloaded vision model to load it as the
active model for the conversation.

## Upload an image

With a vision-capable (local, not cloud) model loaded, in either app:

1. Drag the image file straight into the chat window, or use the chat
   window's attach/add-file icon next to the message box — both add the
   image to your next message.
2. Type your question — e.g. *"What does this image show?"*
3. Send the message.

The image thumbnail appears in the chat alongside your message, and the
model's answer streams in below it, the same as a text-only reply.

## Troubleshooting

- No way to attach an image, or the model ignores it — the loaded model is
  text-only; switch to a vision-capable model (see above).
- Nothing happens when opening Ollama from the menu bar — its background
  service may not be running; reopen the app, or run `ollama serve` in a
  terminal.
- LM Studio's model dropdown is empty — you haven't downloaded a model yet;
  go back to **Discover**.
- Slow first response after uploading an image — the model is loading into
  memory; it's faster on the next message as long as it stays loaded.
- To free disk space: in Ollama, remove a model from the chat window's
  manage-models view or run `ollama rm <model>`; in LM Studio, remove it
  from the **My Models** tab.
- To be certain you'll never accidentally run a (paid) cloud model: in
  Ollama, set `OLLAMA_NO_CLOUD=1` in your environment (or
  `"disable_ollama_cloud": true` in `~/.ollama/server.json`) and restart; in
  LM Studio, don't sign in to an account, and check that the model picker
  shows your chosen model under **Local**, not **Cloud**.
