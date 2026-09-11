"""Strongly-typed tool registry.

Every capability the model can invoke is a :class:`Tool` with JSON schemas,
permissions, limits and provenance. Built-in tools are registered in
:mod:`aimathh.tools.builtin`.
"""

from aimathh.tools.registry import (
    Tool,
    ToolContext,
    ToolRegistry,
    ToolSpec,
    get_tool_registry,
    register_tool,
    tool,
)
from aimathh.tools import builtin  # noqa: F401  (registers built-ins on import)

__all__ = [
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "ToolSpec",
    "get_tool_registry",
    "register_tool",
    "tool",
]
