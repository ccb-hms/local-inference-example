"""Tiny toolset the agent can call."""

from __future__ import annotations

import ast
import datetime
import operator
from collections.abc import Callable

_OPS: dict[type, Callable[..., float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"unsupported expression: {ast.dump(node)}")


def calculator(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression, e.g. '12 * (3 + 4)'."""
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_eval_node(tree.body))
    except Exception as exc:  # noqa: BLE001 - surfaced to the model as an observation
        return f"error: could not evaluate '{expression}' ({exc})"


def get_time() -> str:
    """Return the current local date and time."""
    return datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")


TOOLS: dict[str, Callable[..., str]] = {
    "calculator": calculator,
    "get_time": get_time,
}
