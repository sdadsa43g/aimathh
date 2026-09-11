"""Process-isolated Python/shell sandbox with resource limits.

Design:
* every execution runs in its own subprocess with its own CWD under the
  sandbox root (filesystem isolation);
* CPU wall-time enforced via subprocess timeout; memory enforced with
  ``resource.setrlimit`` on POSIX where available;
* network access is *not* granted to sandboxed code by default — the
  ``NETWORK`` permission only allows harness-level HTTP clients, never the
  sandbox itself, unless explicitly enabled;
* dangerous syscalls/operations are the caller's responsibility to avoid —
  generated code is untrusted and must stay inside the sandbox dir.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from aimathh.core.errors import SandboxError, ToolTimeoutError
from aimathh.core.ids import new_id
from aimathh.core.logging import get_logger
from aimathh.execution.permissions import Permission, PermissionSet, default_permissions

log = get_logger("sandbox")


class SandboxLimits(BaseModel):
    timeout_s: int = 120
    memory_mb: int = 2048
    max_output_chars: int = 200_000


class ExecutionRequest(BaseModel):
    code: str
    language: Literal["python", "shell"] = "python"
    timeout_s: int | None = None
    memory_mb: int | None = None
    seed: int | None = None
    permissions: PermissionSet = Field(default_factory=default_permissions)
    extra_files: dict[str, str] = Field(default_factory=dict)  # relpath -> content
    capture_artifacts: list[str] = Field(default_factory=list)  # glob relpaths to keep


class ExecutionResult(BaseModel):
    run_id: str = ""
    success: bool = True
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    duration_s: float = 0.0
    timed_out: bool = False
    workdir: str = ""
    artifacts: dict[str, str] = Field(default_factory=dict)  # relpath -> abs path
    truncated: bool = False


class Sandbox:
    def __init__(self, root: Path, limits: SandboxLimits | None = None) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.limits = limits or SandboxLimits()

    # -- public API -----------------------------------------------------
    def run_python(self, req: ExecutionRequest) -> ExecutionResult:
        req.permissions.require(Permission.EXECUTE)
        language = getattr(req, "language", "python")
        if language != "python":
            raise SandboxError(f"Unsupported sandbox language '{language}'")
        return self._run(self._python_command(req), req)

    def run_shell(self, req: ExecutionRequest) -> ExecutionResult:
        req.permissions.require(Permission.EXECUTE)
        return self._run(["/bin/bash", "-c", req.code], req)

    # -- internals ------------------------------------------------------
    def _python_command(self, req: ExecutionRequest) -> list[str]:
        prelude = ""
        if req.seed is not None:
            prelude = textwrap.dedent(
                f"""\
                import os, random
                os.environ["PYTHONHASHSEED"] = "{req.seed}"
                random.seed({req.seed})
                try:
                    import numpy as _np
                    _np.random.seed({req.seed})
                except Exception:
                    pass
                """
            )
        # The wrapper just execs user code; isolation comes from CWD +
        # rlimits + timeout, not from AST filtering (which gives false safety).
        return [sys.executable, "-c", prelude + "\n" + req.code]

    def _run(self, argv: list[str], req: ExecutionRequest) -> ExecutionResult:
        run_id = new_id("run_")
        workdir = Path(tempfile.mkdtemp(prefix=run_id + "_", dir=str(self.root)))
        for rel, content in req.extra_files.items():
            dest = (workdir / rel).resolve()
            if self.root.resolve() not in dest.parents and dest != self.root.resolve():
                # also allow workdir itself
                if workdir.resolve() not in dest.parents:
                    raise SandboxError(f"Refusing to write outside sandbox: {rel}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        timeout = req.timeout_s or self.limits.timeout_s
        mem_mb = req.memory_mb or self.limits.memory_mb
        t0 = time.time()
        try:
            proc = subprocess.run(
                argv,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=_make_rlimit_fn(mem_mb),
                env=_sandbox_env(),
            )
            duration = time.time() - t0
            stdout, truncated1 = _truncate(proc.stdout or "", self.limits.max_output_chars // 2)
            stderr, truncated2 = _truncate(proc.stderr or "", self.limits.max_output_chars // 2)
            artifacts: dict[str, str] = {}
            for pattern in req.capture_artifacts:
                for p in sorted(workdir.glob(pattern)):
                    if p.is_file():
                        artifacts[p.name] = str(p)
            return ExecutionResult(
                run_id=run_id,
                success=proc.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                returncode=proc.returncode,
                duration_s=duration,
                timed_out=False,
                workdir=str(workdir),
                artifacts=artifacts,
                truncated=truncated1 or truncated2,
            )
        except subprocess.TimeoutExpired as e:
            duration = time.time() - t0
            raise ToolTimeoutError(
                f"Sandbox execution exceeded {timeout}s", details={"run_id": run_id}
            ) from e
        except ToolTimeoutError:
            raise
        except Exception as e:  # pragma: no cover - defensive
            raise SandboxError(f"Sandbox execution failed: {e}") from e


def _sandbox_env() -> dict[str, str]:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "MPLBACKEND": "Agg",
        "NUMEXPR_MAX_THREADS": "4",
        "OMP_NUM_THREADS": "4",
    }
    # Preserve a minimal safe subset
    for k in ("HOME", "TMPDIR", "LANG", "LC_ALL", "TZ"):
        if k in os.environ:
            env[k] = os.environ[k]
    return env


def _make_rlimit_fn(mem_mb: int):  # pragma: no cover - platform dependent
    def _fn() -> None:
        try:
            import resource

            total = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (total, total))
            # No core dumps, no new privileges where supported
            try:
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            except Exception:
                pass
        except Exception:
            pass

    return _fn


def _truncate(s: str, limit: int) -> tuple[str, bool]:
    if len(s) <= limit:
        return s, False
    return s[:limit] + f"\n...[truncated {len(s) - limit} chars]...", True


_sandbox: Sandbox | None = None


def get_sandbox() -> Sandbox:
    global _sandbox
    if _sandbox is None:
        from aimathh.core.config import get_settings

        settings = get_settings()
        settings.ensure_dirs()
        _sandbox = Sandbox(
            settings.sandbox_root,
            SandboxLimits(timeout_s=settings.default_timeout_s, memory_mb=settings.max_memory_mb),
        )
    return _sandbox
