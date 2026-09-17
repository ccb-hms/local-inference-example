"""FastAPI backend: one endpoint that runs the agent loop, plus static files
for the plain-JS chat + chart frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import run_agent
from .model import LocalLLM

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="local-inference-example")
_llm: LocalLLM | None = None


def get_llm() -> LocalLLM:
    global _llm
    if _llm is None:
        _llm = LocalLLM()
    return _llm


class ChatRequest(BaseModel):
    message: str


class TranscriptEntryOut(BaseModel):
    kind: str
    text: str
    detail: dict | None = None


class ChatResponse(BaseModel):
    transcript: list[TranscriptEntryOut]
    answer: str
    chart: dict | None = None


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = run_agent(get_llm(), request.message)
    return ChatResponse(
        transcript=[
            TranscriptEntryOut(kind=entry.kind, text=entry.text, detail=entry.detail)
            for entry in result.transcript
        ],
        answer=result.answer,
        chart=result.chart,
    )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
