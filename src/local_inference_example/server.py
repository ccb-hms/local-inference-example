"""FastAPI backend: streams the agent loop over Server-Sent Events as each
step actually happens, plus static files for the plain-JS chat + chart
frontend."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent import run_agent_stream
from .model import DEFAULT_MODEL, LocalLLM

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="local-inference-example")
_llm: LocalLLM | None = None
model_name = DEFAULT_MODEL


def get_llm() -> LocalLLM:
    global _llm
    if _llm is None:
        _llm = LocalLLM(model_name=model_name)
    return _llm


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/chat/stream")
def chat_stream(message: str) -> StreamingResponse:
    """Server-Sent Events: one "step" event per TranscriptEntry, the
    instant run_agent_stream produces it - not a replay of an
    already-finished run. Model inference is blocking, but FastAPI runs a
    sync generator like this one in a thread pool, so it doesn't block the
    event loop for other requests."""

    def events():
        for entry in run_agent_stream(get_llm(), message):
            yield _sse(
                "step",
                {
                    "kind": entry.kind,
                    "text": entry.text,
                    "detail": entry.detail,
                    "chart": entry.chart,
                },
            )
        yield _sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
