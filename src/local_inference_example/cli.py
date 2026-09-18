"""Entry point: launches the web app and opens it in a browser.

The model itself loads lazily on the first chat request (see server.py),
not at server startup, so this returns instantly.
"""

from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn

from . import server
from .model import DEFAULT_MODEL_SIZE, MODEL_SIZES

HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    parser = argparse.ArgumentParser(description="local-inference-example")
    parser.add_argument(
        "--model-size",
        choices=sorted(MODEL_SIZES),
        default=DEFAULT_MODEL_SIZE,
        help=(
            "Qwen2.5-Instruct size to run. 0.5b is smaller/faster but noticeably "
            "less reliable at picking the right tool - see the README's "
            "outlines-vs-native comparison. Default: %(default)s."
        ),
    )
    args = parser.parse_args()
    server.model_name = MODEL_SIZES[args.model_size]

    url = f"http://{HOST}:{PORT}"
    print(f"Starting local-inference-example at {url} (model: {server.model_name})")
    print("(the model loads on your first question - that'll take a moment)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("local_inference_example.server:app", host=HOST, port=PORT)
