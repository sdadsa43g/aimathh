"""Sandbox isolation + tool registry behavior."""

import pytest

from aimathh.core.errors import PermissionDeniedError, ToolNotFoundError
from aimathh.execution.permissions import Permission, PermissionSet
from aimathh.execution.sandbox import ExecutionRequest, get_sandbox
from aimathh.tools import get_tool_registry
from aimathh.tools.registry import ToolContext


def test_python_exec_basic():
    res = get_sandbox().run_python(ExecutionRequest(code="print(2+2)"))
    assert res.success and res.stdout.strip() == "4"


def test_python_exec_failure_captured():
    res = get_sandbox().run_python(ExecutionRequest(code="raise ValueError('boom')"))
    assert not res.success
    assert "boom" in res.stderr


def test_python_exec_timeout():
    import pytest as _p

    from aimathh.core.errors import ToolTimeoutError

    with _p.raises(ToolTimeoutError):
        get_sandbox().run_python(ExecutionRequest(code="import time; time.sleep(30)", timeout_s=1))


def test_permission_denied():
    ctx = ToolContext(permissions=PermissionSet(allowed={Permission.READ}))
    with pytest.raises(PermissionDeniedError):
        ctx.permissions.require(Permission.NETWORK)


def test_unknown_tool():
    import asyncio

    with pytest.raises(ToolNotFoundError):
        asyncio.run(get_tool_registry().call("no_such_tool", {}, ToolContext()))


def test_tool_call_records_provenance(tool_ctx):
    import asyncio

    res = asyncio.run(get_tool_registry().call("symbolic", {"op": "simplify", "expr": "1+1"}, tool_ctx))
    assert res.ok
    assert res.provenance is not None
    assert res.provenance.tool == "symbolic"
    assert len(tool_ctx.provenance) == 1


def test_tool_stats_tracked(tool_ctx):
    import asyncio

    reg = get_tool_registry()
    before = reg.stats["numeric"]["calls"]
    asyncio.run(reg.call("numeric", {"op": "evaluate", "expr": "1+1"}, tool_ctx))
    assert reg.stats["numeric"]["calls"] == before + 1
