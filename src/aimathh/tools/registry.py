"""Tool definitions, registry, execution with provenance + observability."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.errors import ToolError, ToolNotFoundError, ToolValidationError
from aimathh.core.ids import new_id
from aimathh.core.logging import get_logger
from aimathh.core.provenance import Provenance, make_provenance
from aimathh.execution.permissions import Permission, PermissionSet, default_permissions

log = get_logger("tools")


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: PermissionSet = Field(default_factory=default_permissions)
    timeout_s: int = 120
    memory_mb: int = 1024
    version: str = "0.1.0"
    tags: list[str] = Field(default_factory=list)


class ToolContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    run_id: str = ""
    experiment_id: str = ""
    permissions: PermissionSet = Field(default_factory=default_permissions)
    seed: int | None = None
    provenance: list[Provenance] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool = True
    output: Any = None
    error: str = ""
    duration_s: float = 0.0
    provenance: Provenance | None = None


ToolFn = Callable[[dict[str, Any], ToolContext], Awaitable[Any] | Any]


class Tool(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    spec: ToolSpec
    fn: ToolFn

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.spec.name,
                "description": self.spec.description,
                "parameters": self.spec.input_schema,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self.stats: dict[str, dict[str, Any]] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool
        self.stats.setdefault(tool.spec.name, {"calls": 0, "errors": 0, "total_s": 0.0})

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolNotFoundError(f"Unknown tool '{name}'", details={"available": sorted(self._tools)})
        return self._tools[name]

    def list_specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def openai_tools(self) -> list[dict[str, Any]]:
        return [t.openai_schema() for t in self._tools.values()]

    async def call(self, name: str, args: dict[str, Any], ctx: ToolContext | None = None) -> ToolResult:
        tool = self.get(name)
        ctx = ctx or ToolContext(run_id=new_id("run_"))
        # Permission check: context must grant everything the tool needs.
        for perm in tool.spec.permissions.allowed:
            ctx.permissions.require(perm)
        prov = make_provenance(
            name, input=dict(args), parameters={"version": tool.spec.version}, seed=ctx.seed
        )
        t0 = time.time()
        try:
            out = tool.fn(dict(args), ctx)
            if inspect.isawaitable(out):
                out = await asyncio.wait_for(out, timeout=tool.spec.timeout_s)
            duration = time.time() - t0
            prov.duration_s = duration
            prov.success = True
            prov.output_digest = _digest(out)
            ctx.provenance.append(prov)
            st = self.stats[name]
            st["calls"] += 1
            st["total_s"] += duration
            log.info("tool %s ok in %.2fs", name, duration, extra={"tool": name})
            return ToolResult(ok=True, output=out, duration_s=duration, provenance=prov)
        except Exception as e:  # noqa: BLE001
            duration = time.time() - t0
            prov.duration_s = duration
            prov.success = False
            prov.error = f"{type(e).__name__}: {e}"
            ctx.provenance.append(prov)
            st = self.stats[name]
            st["calls"] += 1
            st["errors"] += 1
            st["total_s"] += duration
            log.error("tool %s failed: %s", name, e, extra={"tool": name})
            if isinstance(e, (ToolError,)):
                raise
            raise ToolError(f"Tool '{name}' failed: {e}") from e


def _digest(out: Any) -> str:
    try:
        blob = json.dumps(out, sort_keys=True, default=str)[:20000]
    except Exception:
        blob = str(out)[:20000]
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _registry


def register_tool(spec: ToolSpec, fn: ToolFn) -> Tool:
    t = Tool(spec=spec, fn=fn)
    _registry.register(t)
    return t


def tool(
    name: str,
    description: str,
    *,
    input_schema: dict[str, Any] | None = None,
    permissions: PermissionSet | None = None,
    timeout_s: int = 120,
    tags: list[str] | None = None,
) -> Callable[[ToolFn], ToolFn]:
    """Decorator registering a function as a tool."""

    def deco(fn: ToolFn) -> ToolFn:
        register_tool(
            ToolSpec(
                name=name,
                description=description,
                input_schema=input_schema or {"type": "object", "properties": {}},
                permissions=permissions or default_permissions(),
                timeout_s=timeout_s,
                tags=tags or [],
            ),
            fn,
        )
        return fn

    return deco


def validate_required(args: dict[str, Any], *keys: str) -> None:
    missing = [k for k in keys if k not in args]
    if missing:
        raise ToolValidationError(f"Missing required arguments: {missing}")
