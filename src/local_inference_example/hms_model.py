"""Talks to the HMS-provisioned inference service instead of running a model
locally (see https://github.com/ccb-hms/LocalAiInferenceService). No
download or GPU/CPU inference on this machine - just an HTTPS call - but it
needs HMS credentials and network access (VPN) to the service.

The service exposes an OpenAI-compatible chat API. It supports tool calling
but not the stricter response_format=json_schema mode, so generate_step
gets the same structural guarantee LocalLLM gets from outlines' constrained
decoding (always a valid AgentStep) by forcing a single tool call whose
parameters schema *is* AgentStep, then parsing that call's arguments -
rather than trusting the model to emit bare matching JSON as its message
text.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from urllib.parse import urlencode

from openai import APIConnectionError, OpenAI, OpenAIError

from .agent import AgentStep

logger = logging.getLogger(__name__)

# Same Okta tenant/app audiotranscription's hmsmodel.py authenticates against -
# this is HMS's shared AI-endpoint login, not something specific to either repo.
OKTA_URL = "https://login.hms.harvard.edu"
OKTA_CLIENT_ID = "0oa139tiylzbW6XnX698"
OKTA_AUTH_SERVER_ID = "aus155lzzptyDTgN3698"
TOKEN_URL = f"{OKTA_URL}/oauth2/{OKTA_AUTH_SERVER_ID}/v1/token"
SCOPE = "openid offline_access"

TOOL_NAME = "agent_step"


def get_access_token(username: str, password: str, timeout: int = 30) -> str | None:
    """Exchanges an HMS username and password for an Okta access token.
    Returns None if the credentials were rejected or the token couldn't be
    retrieved. Uses curl (not requests/httpx) so the credentials are only
    ever handed to a subprocess over stdin, never built into a URL or log
    line that could end up somewhere unexpected."""
    data = urlencode(
        {
            "client_id": OKTA_CLIENT_ID,
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": SCOPE,
        }
    )
    cmd = [
        "curl", "--silent", "--show-error", "--request", "POST",
        "--url", TOKEN_URL,
        "--header", "Accept: application/json",
        "--header", "Content-Type: application/x-www-form-urlencoded",
        "--data", "@-",
    ]
    try:
        result = subprocess.run(
            cmd, input=data, capture_output=True, text=True, timeout=timeout, check=True
        )
    except FileNotFoundError:
        logger.error("curl was not found on this system.")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"The request to {TOKEN_URL} timed out after {timeout} seconds.")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"curl failed with exit code {e.returncode}: {e.stderr.strip()}")
        return None

    # Okta returns HTTP 200 with an error body on bad credentials, so check
    # for the token itself rather than curl's exit status.
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error(f"Could not parse the Okta response: {result.stdout}")
        return None
    token = response.get("access_token")
    if token is None:
        logger.error(f"Failed to authenticate, check below error\n{result.stdout}")
    return token


def _resolve_token() -> str:
    """HMS_API_TOKEN (an already-issued access token) wins if set - simplest
    option, and the only one that works without an interactive HMS password.
    Otherwise fall back to exchanging HMS_USERNAME/HMS_PASSWORD for one."""
    token = os.environ.get("HMS_API_TOKEN")
    if token:
        return token
    username = os.environ.get("HMS_USERNAME")
    password = os.environ.get("HMS_PASSWORD")
    if not (username and password):
        raise RuntimeError(
            "No HMS credentials configured. Set HMS_API_TOKEN, or both HMS_USERNAME and "
            "HMS_PASSWORD, in your environment - see README.md's HMS inference service section."
        )
    token = get_access_token(username, password)
    if token is None:
        raise RuntimeError(
            "Failed to authenticate with the HMS inference service - check "
            "HMS_USERNAME/HMS_PASSWORD and that you're connected to the HMS VPN."
        )
    return token


class HMSLLM:
    """Same generate_step(messages) -> AgentStep interface as LocalLLM (see
    agent.ChatModel), backed by the HMS inference service instead of a
    model downloaded and run on this machine."""

    def __init__(self, model: str | None = None, endpoint: str | None = None, token: str | None = None):
        self.endpoint = endpoint or os.environ.get("HMS_API_ENDPOINT")
        if not self.endpoint:
            raise RuntimeError(
                "HMS_API_ENDPOINT is not set - see README.md's HMS inference service section."
            )
        self.device = "HMS inference service"  # shown by /api/status in place of a local device
        self.client = OpenAI(base_url=f"{self.endpoint}/v1", api_key=token or _resolve_token())
        # Always list models, even when one was requested explicitly: this is the first real
        # network call to the service, so it surfaces a VPN/connectivity problem here - the same
        # "fail before the server opens" spirit as LocalLLM's eager download/load - rather than
        # only on the first chat message, several steps into a stream.
        available = self._list_models()
        self.model = model or os.environ.get("HMS_MODEL") or self._pick_default(available)

    def _list_models(self) -> list[str]:
        try:
            return [m.id for m in self.client.models.list().data]
        except OpenAIError as e:
            raise RuntimeError(self._connection_error_message(e)) from e

    def _pick_default(self, available: list[str]) -> str:
        """No model requested - use the first one the service reports, the same
        "just give me something that works" default LocalLLM's DEFAULT_MODEL
        constant hardcodes for the local backend."""
        if not available:
            raise RuntimeError(f"The HMS inference service at {self.endpoint} has no models available.")
        return available[0]

    def _connection_error_message(self, e: OpenAIError) -> str:
        """APIConnectionError covers DNS failures, refused connections, and timeouts alike -
        all symptoms of the same most-likely cause here, since the service is only reachable
        from the HMS VPN (see the Troubleshooting table in LocalAiInferenceService's README)."""
        if isinstance(e, APIConnectionError):
            return (
                f"Could not reach {self.endpoint} - are you connected to the HMS VPN? "
                f"The service is unreachable without it. ({e})"
            )
        return f"HMS inference service at {self.endpoint} rejected the request: {e}"

    def generate_step(self, messages: list[dict[str, str]]) -> AgentStep:
        """Turn the conversation so far into one validated next step, via a
        forced tool call rather than trusting free-text JSON."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                tools=[
                    {
                        "type": "function",
                        "function": {"name": TOOL_NAME, "parameters": AgentStep.model_json_schema()},
                    }
                ],
                tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
            )
        except OpenAIError as e:
            raise RuntimeError(self._connection_error_message(e)) from e
        if not response.choices:
            raise RuntimeError(f"No message in the response from {self.model}: {response.model_dump()}")
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise RuntimeError(f"No tool call in the response from {self.model}: {response.model_dump()}")
        return AgentStep.model_validate_json(tool_calls[0].function.arguments)
