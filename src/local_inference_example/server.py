"""FastAPI backend: streams the agent loop over Server-Sent Events as each
step actually happens, plus static files for the plain-JS chat + chart
frontend."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent import ChatModel, run_agent_stream
from .model import DEFAULT_MODEL, LocalLLM

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="local-inference-example")
_llm: ChatModel | None = None  # loaded eagerly by cli.main() before the server starts
backend = "local"  # or "hms" - set by cli.main() before get_llm() is first called
model_name = DEFAULT_MODEL  # local backend only: HF repo id
hms_model_name: str | None = None  # hms backend only: None = ask the service for its default


def get_llm() -> ChatModel:
    """Load the model on first call, then reuse the same instance for every later request."""
    global _llm
    if _llm is None:
        if backend == "hms":
            from .hms_model import HMSLLM  # deferred: only needed for this backend

            _llm = HMSLLM(model=hms_model_name)
        else:
            _llm = LocalLLM(model_name=model_name)
    return _llm


@app.get("/api/status")
def status() -> dict:
    """Which model and device are actually running, so the frontend can
    show a "running on CPU, this will be slow" banner instead of leaving a
    multi-minute wait unexplained. cli.py loads the model before the server
    starts, so get_llm() here is always a cheap cache hit, never a load."""
    llm = get_llm()
    name = llm.model if backend == "hms" else llm.model_name
    return {"model": name, "device": llm.device}


def _sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event message: a labeled chunk the browser can read as it arrives."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/chat/stream")
def chat_stream(message: str) -> StreamingResponse:
    """Server-Sent Events: one "step" event per TranscriptEntry, the
    instant run_agent_stream produces it - not a replay of an
    already-finished run. Model inference is blocking, but FastAPI runs a
    sync generator like this one in a thread pool, so it doesn't block the
    event loop for other requests."""

    def events():
        for entry in run_agent_stream(get_llm(), message):  # yields one step at a time, live
            yield _sse(
                "step",
                {
                    "kind": entry.kind,
                    "text": entry.text,
                    "detail": entry.detail,
                    "chart": entry.chart,
                },
            )
        yield _sse("done", {})  # tell the browser the conversation turn is complete

    return StreamingResponse(events(), media_type="text/event-stream")


# Serve the frontend (index.html, app.js, style.css) for every other URL.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
