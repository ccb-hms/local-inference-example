"""Tool: real-world state the model can't know on its own."""

from __future__ import annotations

import datetime

from . import ToolResult


def get_time() -> ToolResult:
    """Return the current local date and time."""
    now = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    return ToolResult(text=now)
