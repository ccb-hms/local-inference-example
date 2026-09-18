"""Tool: real-world state the model can't know on its own."""

from __future__ import annotations

import datetime

from . import ToolResult


def get_time() -> ToolResult:
    """Return the current local date and time."""
    now = datetime.datetime.now()  # read the computer's clock
    return ToolResult(
        text=now.strftime("%A, %Y-%m-%d %H:%M:%S"),  # human-readable, e.g. "Tuesday, 2026-09-18"
        raw_data={"iso": now.isoformat()},  # machine-readable version, for the "data" inspector
    )
