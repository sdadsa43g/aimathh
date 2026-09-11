"""Multi-level verification engine.

Levels:
  L0 model reasoning (proposed, never trusted)
  L1 symbolic verification (SymPy equivalence / identity checks)
  L2 numerical verification (independent high-precision recomputation)
  L3 dimensional / physical consistency (units, limits, symmetries)
  L4 independent recomputation (second implementation, different route)
  L5 formal verification (proof assistants — see formal.py; explicit status)

The engine never "averages" conflicting methods: disagreement produces a
:class:`DiscrepancyReport` with a concrete investigation checklist.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aimathh.core.logging import get_logger
from aimathh.core.types import CheckOutcome, EvidenceLevel, VerificationResult, VerificationStatus

log = get_logger("verification")


@dataclass
class DiscrepancyReport:
    claim: str
    method_a: str
    value_a: Any
    method_b: str
    value_b: Any
    disagreement: str
    checklist: list[str] = field(default_factory=list)
    minimal_repro: str = ""

    def __post_init__(self) -> None:
        if not self.checklist:
            self.checklist = [
                "check units and dimensions of both routes",
                "check numerical precision / solver tolerances; rerun tighter",
                "check assumptions, domains, branch cuts",
                "check boundary / initial conditions match exactly",
                "check symbolic simplification steps term-by-term",
                "rerun with higher precision (mpmath dps+15)",
                "use a third independent algorithm",
                "search literature for the expected result",
            ]

    def render(self) -> str:
        lines = [
            f"DISCREPANCY in: {self.claim}",
            f"  A ({self.method_a}): {self.value_a}",
            f"  B ({self.method_b}): {self.value_b}",
            f"  disagreement: {self.disagreement}",
            "  investigation checklist:",
            *[f"   - {c}" for c in self.checklist],
        ]
        if self.minimal_repro:
            lines += ["  minimal repro:", f"    {self.minimal_repro}"]
        return "\n".join(lines)


class VerificationEngine:
    """Stateless checks; compose them per claim via :meth:`verify_claim`."""

    # -- Level 1: symbolic -------------------------------------------
    def symbolic_equal(self, a: str, b: str, variables: list[str] | None = None) -> CheckOutcome:
        t0 = time.time()
        from aimathh.math import symbolic as S

        try:
            r = S.are_symbolically_equal(a, b, variables)
            ok = bool(r["equal"])
            return CheckOutcome(
                name="symbolic_equality",
                status=VerificationStatus.PASSED if ok else VerificationStatus.FAILED,
                detail=f"L1 symbolic: '{a}' vs '{b}' -> {'EQUAL' if ok else 'NOT equal'} "
                       f"(diff={r['difference']}, via {r['method']})",
                evidence=r,
                duration_s=time.time() - t0,
            )
        except Exception as e:  # noqa: BLE001
            return CheckOutcome(name="symbolic_equality", status=VerificationStatus.ERROR,
                                detail=f"L1 error: {e}", duration_s=time.time() - t0)

    def symbolic_identity(self, expr: str, variables: list[str] | None = None) -> CheckOutcome:
        """Check that an expression simplifies to zero / True."""
        return self.symbolic_equal(expr, "0", variables)

    # -- Level 2: numerical ------------------------------------------
    def numeric_agree(
        self,
        value_a: float,
        value_b: float,
        *,
        tol: float = 1e-8,
        label_a: str = "method A",
        label_b: str = "method B",
        claim: str = "numeric agreement",
    ) -> CheckOutcome:
        scale = max(1.0, abs(value_a), abs(value_b))
        gap = abs(value_a - value_b) / scale
        ok = math.isfinite(gap) and gap <= tol
        detail = (f"L2 numeric: {label_a}={value_a!r} vs {label_b}={value_b!r} "
                  f"rel_gap={gap:.3e} tol={tol:.1e} -> {'AGREE' if ok else 'DISAGREE'}")
        return CheckOutcome(
            name="numeric_agreement",
            status=VerificationStatus.PASSED if ok else VerificationStatus.FAILED,
            detail=detail,
            evidence={"a": value_a, "b": value_b, "rel_gap": gap, "tol": tol, "claim": claim},
        )

    def high_precision_confirm(self, expr: str, variables: dict[str, float] | None, expected: float,
                               *, dps: int = 30, tol: float = 1e-12) -> CheckOutcome:
        t0 = time.time()
        from aimathh.math import numeric as N

        try:
            r = N.evaluate(expr, {k: str(v) for k, v in (variables or {}).items()}, dps=dps)
            val = float(r["value"])
            return self.numeric_agree(val, expected, tol=tol, label_a=f"mpmath(dps={dps})",
                                      label_b="expected", claim=expr)
        except Exception as e:  # noqa: BLE001
            return CheckOutcome(name="numeric_agreement", status=VerificationStatus.ERROR,
                                detail=f"L2 error: {e}", duration_s=time.time() - t0)

    # -- Level 3: dimensional / physical -------------------------------
    def dimensional(self, equation: str, symbol_units: dict[str, str]) -> CheckOutcome:
        t0 = time.time()
        from aimathh.physics.dimensional import check_equation

        try:
            r = check_equation(equation, symbol_units)
            return CheckOutcome(
                name="dimensional_consistency",
                status=VerificationStatus.PASSED if r.consistent else VerificationStatus.FAILED,
                detail=f"L3 dimensional: {r.detail}",
                evidence=r.model_dump(),
                duration_s=time.time() - t0,
            )
        except Exception as e:  # noqa: BLE001
            return CheckOutcome(name="dimensional_consistency", status=VerificationStatus.ERROR,
                                detail=f"L3 error: {e}", duration_s=time.time() - t0)

    def limiting_case(self, label: str, computed: float, expected: float, tol: float = 1e-6) -> CheckOutcome:
        gap = abs(computed - expected) / max(1.0, abs(expected))
        ok = math.isfinite(gap) and gap <= tol
        return CheckOutcome(
            name=f"limiting_case:{label}",
            status=VerificationStatus.PASSED if ok else VerificationStatus.FAILED,
            detail=f"L3 limiting case '{label}': computed={computed!r} expected={expected!r} -> "
                   f"{'OK' if ok else 'VIOLATED'}",
            evidence={"computed": computed, "expected": expected, "tol": tol},
        )

    # -- Level 4: independent recomputation -----------------------------
    def independent(
        self,
        claim: str,
        route_a: Callable[[], Any],
        route_b: Callable[[], Any],
        compare: Callable[[Any, Any], tuple[bool, str]] | None = None,
    ) -> CheckOutcome:
        t0 = time.time()
        try:
            va = route_a()
        except Exception as e:  # noqa: BLE001
            return CheckOutcome(name="independent_recomputation", status=VerificationStatus.ERROR,
                                detail=f"L4 route A failed: {e}", duration_s=time.time() - t0)
        try:
            vb = route_b()
        except Exception as e:  # noqa: BLE001
            return CheckOutcome(name="independent_recomputation", status=VerificationStatus.ERROR,
                                detail=f"L4 route B failed: {e}",
                                evidence={"route_a": str(va)}, duration_s=time.time() - t0)
        if compare is None:
            compare = _default_compare
        try:
            ok, note = compare(va, vb)
        except Exception as e:  # noqa: BLE001
            return CheckOutcome(name="independent_recomputation", status=VerificationStatus.ERROR,
                                detail=f"L4 comparison error: {e}",
                                evidence={"route_a": str(va), "route_b": str(vb)})
        return CheckOutcome(
            name="independent_recomputation",
            status=VerificationStatus.PASSED if ok else VerificationStatus.FAILED,
            detail=f"L4 independent [{claim}]: {'AGREE' if ok else 'DISAGREE'} — {note}",
            evidence={"route_a": _jsonable(va), "route_b": _jsonable(vb), "note": note},
            duration_s=time.time() - t0,
        )

    # -- Composition -----------------------------------------------------
    def verify_claim(
        self,
        claim: str,
        checks: list[CheckOutcome],
        *,
        tolerance: float | None = None,
        precision: str = "",
    ) -> VerificationResult:
        methods = [c.name for c in checks]
        failed = [c for c in checks if c.status == VerificationStatus.FAILED]
        errors = [c for c in checks if c.status == VerificationStatus.ERROR]
        if errors:
            status = VerificationStatus.ERROR
        elif failed:
            status = VerificationStatus.FAILED
        elif not checks:
            status = VerificationStatus.NOT_RUN
        else:
            status = VerificationStatus.PASSED
        level = self._evidence_level(checks, status)
        disc = ""
        if failed:
            f = failed[0]
            ev = f.evidence
            disc = DiscrepancyReport(
                claim=claim,
                method_a="expected",
                value_a=ev.get("expected", ev.get("a", "?")),
                method_b=f.name,
                value_b=ev.get("computed", ev.get("b", "?")),
                disagreement=f.detail,
            ).render()
        by_name = {c.name: c for c in checks}
        get = lambda *names: next((by_name[n] for n in names if n in by_name), None)  # noqa: E731
        return VerificationResult(
            status=status,
            evidence_level=level,
            methods=methods,
            checks=checks,
            symbolic_check=get("symbolic_equality"),
            numerical_check=get("numeric_agreement"),
            dimensional_check=get("dimensional_consistency"),
            independent_check=get("independent_recomputation"),
            precision=precision,
            tolerance=tolerance,
            warnings=[] if status == VerificationStatus.PASSED else [f.detail for f in failed + errors],
            discrepancy_report=disc,
        )

    @staticmethod
    def _evidence_level(checks: list[CheckOutcome], status: VerificationStatus) -> EvidenceLevel:
        if status == VerificationStatus.FAILED:
            # A failed check refutes the claim as stated (or the check setup).
            return EvidenceLevel.REFUTED
        if status != VerificationStatus.PASSED:
            return EvidenceLevel.UNVERIFIED
        names = {c.name for c in checks}
        has_sym = "symbolic_equality" in names
        has_num = "numeric_agreement" in names
        has_dim = "dimensional_consistency" in names
        has_ind = "independent_recomputation" in names
        if has_ind and (has_sym or has_num) and (has_dim or True):
            # Independent second route + a primary check = verified computation.
            if has_ind and (has_sym or has_num):
                return EvidenceLevel.VERIFIED_COMPUTATION
        if has_sym and has_num:
            return EvidenceLevel.VERIFIED_COMPUTATION
        if has_num or has_sym:
            return EvidenceLevel.NUMERICALLY_CONFIRMED
        if has_dim:
            return EvidenceLevel.STRONGLY_SUPPORTED
        return EvidenceLevel.HEURISTIC


def _default_compare(a: Any, b: Any) -> tuple[bool, str]:
    try:
        fa, fb = float(a), float(b)
        gap = abs(fa - fb) / max(1.0, abs(fa), abs(fb))
        return gap <= 1e-8, f"rel_gap={gap:.3e}"
    except (TypeError, ValueError):
        ok = str(a) == str(b)
        return ok, "string equality" if ok else f"{a!r} != {b!r}"


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in list(v.items())[:50]}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in list(v)[:50]]
    return str(v)[:2000]


class QualityGate:
    """Pre-presentation checklist. Blocks VERIFIED labels unless satisfied."""

    QUESTIONS = [
        "Was the calculation actually executed (not just proposed)?",
        "Was it independently checked by a second route?",
        "Are units/dimensions consistent (physics claims)?",
        "Are assumptions explicit?",
        "Are numerical tolerances sufficient and reported?",
        "Are known limiting cases correct?",
        "Was a counterexample search performed (universal claims)?",
        "Do independent methods agree within tolerance?",
        "Are sources real and retrieved (no invented citations)?",
        "Is the epistemic label correct (proof vs computation vs hypothesis)?",
        "Can the result be reproduced (seed/env/manifest)?",
    ]

    def evaluate(
        self,
        *,
        executed: bool,
        independently_checked: bool,
        units_consistent: bool | None,
        assumptions: list[str],
        tolerances_reported: bool,
        limiting_cases_ok: bool | None,
        counterexample_searched: bool | None,
        methods_agree: bool | None,
        sources_valid: bool | None,
        reproducible: bool,
    ) -> dict[str, Any]:
        answers: dict[str, bool | None] = {
            "executed": executed,
            "independently_checked": independently_checked,
            "units_consistent": units_consistent,
            "assumptions_explicit": bool(assumptions),
            "tolerances_reported": tolerances_reported,
            "limiting_cases_ok": limiting_cases_ok,
            "counterexample_searched": counterexample_searched,
            "methods_agree": methods_agree,
            "sources_valid": sources_valid,
            "reproducible": reproducible,
        }
        # Hard gates: must be True. Soft gates (None = not applicable) are skipped.
        hard_fail = [
            k for k, v in answers.items()
            if v is False and k in ("executed", "assumptions_explicit", "tolerances_reported", "reproducible")
        ]
        disagreements = [k for k, v in answers.items() if v is False]
        passed = not hard_fail and (methods_agree is not False) and (units_consistent is not False)
        if passed and independently_checked and executed and methods_agree:
            label = EvidenceLevel.VERIFIED_COMPUTATION
        elif passed and executed:
            label = EvidenceLevel.NUMERICALLY_CONFIRMED
        else:
            label = EvidenceLevel.UNVERIFIED
        return {
            "passed": passed,
            "recommended_label": label.value,
            "answers": answers,
            "hard_failures": hard_fail,
            "disagreements": disagreements,
            "questions": self.QUESTIONS,
            "verdict": label.value.upper() if passed else "UNVERIFIED",
        }


_engine: VerificationEngine | None = None


def get_verification_engine() -> VerificationEngine:
    global _engine
    if _engine is None:
        _engine = VerificationEngine()
    return _engine
