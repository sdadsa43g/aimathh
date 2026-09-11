"""Level 5 — formal verification integrations (extensible, honest stubs).

The architecture defines a ``ProverBackend`` interface with discovery,
version reporting and explicit capability flags. Backends that require an
external toolchain (Lean, Coq, Isabelle, Z3) report ``available=False`` with
install instructions instead of faking results.

Z3 (if installed) IS wired as a real backend because it is pip-installable.
"""

from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from aimathh.core.errors import NotImplementedSubsystemError


class ProverCapabilities(BaseModel):
    name: str
    available: bool
    version: str = ""
    reason: str = ""
    supports_smt: bool = False
    supports_proof_checking: bool = False
    install_hint: str = ""


class ProverBackend(ABC):
    name: str = "base"

    @abstractmethod
    def capabilities(self) -> ProverCapabilities:
        raise NotImplementedError

    @abstractmethod
    def check(self, problem: dict[str, Any]) -> dict[str, Any]:
        """Run the prover. Must raise NotImplementedSubsystemError if unavailable."""
        raise NotImplementedError


class Z3Backend(ProverBackend):
    """SMT solving via z3-solver (pip-installable)."""

    name = "z3"

    def capabilities(self) -> ProverCapabilities:
        try:
            import z3  # noqa: F401

            return ProverCapabilities(
                name="z3", available=True, version=_z3_version(),
                supports_smt=True, supports_proof_checking=False,
            )
        except ImportError:
            return ProverCapabilities(
                name="z3", available=False,
                reason="z3-solver is not installed",
                supports_smt=True,
                install_hint="pip install z3-solver",
            )

    def check(self, problem: dict[str, Any]) -> dict[str, Any]:
        caps = self.capabilities()
        if not caps.available:
            raise NotImplementedSubsystemError(
                "Z3 backend unavailable: z3-solver not installed. Hint: pip install z3-solver"
            )
        kind = problem.get("kind", "smt2")
        if kind != "smt2":
            raise ValueError(f"Z3 backend supports kind='smt2', got '{kind}'")
        return _run_z3_smt2(problem["smt2"], timeout_s=int(problem.get("timeout_s", 30)))


def _z3_version() -> str:
    try:
        import z3

        return str(z3.get_version_string())
    except Exception:
        return ""


def _run_z3_smt2(smt2: str, timeout_s: int = 30) -> dict[str, Any]:
    import z3

    vec = z3.parse_smt2_string(smt2)
    if isinstance(vec, z3.AstVector):
        assertions = [vec[i] for i in range(vec.num_args()) if z3.is_expr(vec[i])]
    else:
        assertions = [vec] if z3.is_expr(vec) else []
    solver = z3.Solver()
    solver.set("timeout", timeout_s * 1000)
    solver.add(*assertions)
    verdict = solver.check()
    out: dict[str, Any] = {"verdict": str(verdict), "backend": "z3"}
    if verdict == z3.sat:
        out["model"] = str(solver.model())
    elif verdict == z3.unsat:
        out["note"] = "unsat: the negated conjecture has no model (within theories)"
    else:
        out["note"] = "unknown/timeout — inconclusive, not a proof"
    return out


class ExternalProverBackend(ProverBackend):
    """Base for toolchains invoked as subprocesses (lean, coq, isabelle)."""

    binary: str = ""
    hint: str = ""

    def capabilities(self) -> ProverCapabilities:
        path = shutil.which(self.binary) if self.binary else None
        if not path:
            return ProverCapabilities(
                name=self.name, available=False,
                reason=f"binary '{self.binary}' not found on PATH",
                supports_proof_checking=True, install_hint=self.hint,
            )
        try:
            proc = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
            ver = (proc.stdout or proc.stderr or "").strip().splitlines()
            version = ver[0][:200] if ver else "unknown"
        except Exception:
            version = "unknown"
        return ProverCapabilities(name=self.name, available=True, version=version,
                                  supports_proof_checking=True)

    def check(self, problem: dict[str, Any]) -> dict[str, Any]:
        caps = self.capabilities()
        if not caps.available:
            raise NotImplementedSubsystemError(
                f"{self.name} backend unavailable: {caps.reason}. {caps.install_hint}"
            )
        raise NotImplementedSubsystemError(
            f"{self.name} proof checking is scaffolded but the elaborated pipeline "
            f"(project setup, lake build, tactic-block verification) is on the roadmap. "
            f"See docs/ROADMAP.md."
        )


class LeanBackend(ExternalProverBackend):
    name = "lean"
    binary = "lean"
    hint = "Install elan: https://lean-lang.org/lean4/doc/setup.html"


class CoqBackend(ExternalProverBackend):
    name = "coq"
    binary = "coqc"
    hint = "Install via opam: opam install coq"


class IsabelleBackend(ExternalProverBackend):
    name = "isabelle"
    binary = "isabelle"
    hint = "Download from https://isabelle.in.tum.de/"


_BACKENDS: dict[str, ProverBackend] = {
    "z3": Z3Backend(),
    "lean": LeanBackend(),
    "coq": CoqBackend(),
    "isabelle": IsabelleBackend(),
}


def list_backends() -> list[ProverCapabilities]:
    return [_BACKENDS[k].capabilities() for k in sorted(_BACKENDS)]


def get_backend(name: str) -> ProverBackend:
    if name not in _BACKENDS:
        raise KeyError(f"Unknown prover backend '{name}'. Known: {sorted(_BACKENDS)}")
    return _BACKENDS[name]
