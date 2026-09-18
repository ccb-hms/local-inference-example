"""Entry point: launches the web app and opens it in a browser.

The model itself loads lazily on the first chat request (see server.py),
not at server startup, so this returns instantly.
"""

from __future__ import annotations

import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    url = f"http://{HOST}:{PORT}"
    print(f"Starting local-inference-example at {url}")
    print("(the model loads on your first question - that'll take a moment)")
    # Open the browser tab a moment after the server starts, once it's ready to answer.
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("local_inference_example.server:app", host=HOST, port=PORT)  # starts the web server
