"""Entry point: launches the web app and opens it in a browser.

The model downloads/loads here, before the server starts, so `uv run
local-inference-example` shows progress up front instead of stalling on
the first chat request.
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import webbrowser

import uvicorn
from dotenv import load_dotenv

from . import server
from .model import DEFAULT_MODEL_SIZE, MODEL_SIZES

HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _port_in_use(host: str, port: int) -> bool:
    """Check before loading the model (which can take a while) rather than
    finding out only once uvicorn tries to bind - uvicorn itself swallows
    that OSError and just sys.exit(3)s, so catching it here wouldn't work."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return True
        return False


def main() -> None:
    load_dotenv()  # picks up a .env in the current directory, e.g. for the --backend hms env vars
    parser = argparse.ArgumentParser(description="local-inference-example")
    parser.add_argument(
        "--model-size",
        choices=sorted(MODEL_SIZES),
        default=DEFAULT_MODEL_SIZE,
        help=(
            "Phi-3.5-Instruct size to run. Only one size is offered today; "
            "the flag exists so a smaller/larger size can be added later "
            "without changing the CLI. Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Hugging Face repo id of a dense, full-precision instruct model to run "
            "instead of --model-size (e.g. a model found with "
            "scripts/find_hardware_model.py). Must be loadable with "
            "transformers' AutoModelForCausalLM - quantized GGUF/MLX/AWQ/EXL2 builds "
            "won't work. Ignored with --backend hms."
        ),
    )
    parser.add_argument(
        "--backend",
        choices=["local", "hms"],
        default="local",
        help=(
            "Which model backend to use. 'local' (default) downloads and runs a model on "
            "this machine. 'hms' sends requests to the HMS-provisioned inference service "
            "instead (see README.md's HMS inference service section) - no download, but "
            "needs HMS credentials and VPN access to the service."
        ),
    )
    parser.add_argument(
        "--hms-model",
        default=None,
        help=(
            "Model id to request from the HMS inference service (--backend hms only). "
            "Defaults to HMS_MODEL, or the first model the service reports if that's unset."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to serve the app on, in case {DEFAULT_PORT} is already taken. Default: %(default)s.",
    )
    args = parser.parse_args()

    if _port_in_use(HOST, args.port):
        print(
            f"Port {args.port} is already in use - pick another with, e.g.: "
            f"uv run local-inference-example --port {args.port + 1}",
            file=sys.stderr,
        )
        sys.exit(1)

    server.backend = args.backend
    server.model_name = args.model or MODEL_SIZES[args.model_size]
    server.hms_model_name = args.hms_model

    print(f"Preparing model: {'HMS inference service' if args.backend == 'hms' else server.model_name}")
    server.get_llm()  # downloads (first run only, local only) and loads before the server opens

    url = f"http://{HOST}:{args.port}"
    print(f"Starting local-inference-example at {url}")
    # Open the browser tab a moment after the server starts, once it's ready to answer.
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("local_inference_example.server:app", host=HOST, port=args.port)  # starts the web server
