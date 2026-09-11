"""Verification engine: catches wrong answers, confirms right ones."""

from aimathh.core.types import EvidenceLevel, VerificationStatus
from aimathh.verification import get_verification_engine

eng = get_verification_engine()


def test_symbolic_catches_false_identity():
    c = eng.symbolic_equal("(x+1)^2", "x^2+1", ["x"])
    assert c.status == VerificationStatus.FAILED


def test_symbolic_confirms_true_identity():
    c = eng.symbolic_equal("sin(x)^2+cos(x)^2", "1", ["x"])
    assert c.status == VerificationStatus.PASSED


def test_numeric_agreement_and_disagreement():
    assert eng.numeric_agree(0.1 + 0.2, 0.3, tol=1e-9).status == VerificationStatus.PASSED
    assert eng.numeric_agree(1.0, 1.1, tol=1e-9).status == VerificationStatus.FAILED


def test_dimensional_gate():
    ok = eng.dimensional("F = m*a", {"F": "newton", "m": "kg", "a": "m/s^2"})
    bad = eng.dimensional("E = m*c", {"E": "joule", "m": "kg", "c": "m/s"})
    assert ok.status == VerificationStatus.PASSED
    assert bad.status == VerificationStatus.FAILED


def test_independent_routes_must_agree():
    c = eng.independent("1+1", lambda: 2, lambda: 1 + 1)
    assert c.status == VerificationStatus.PASSED
    c2 = eng.independent("wrong", lambda: 2, lambda: 3)
    assert c2.status == VerificationStatus.FAILED


def test_evidence_ladder():
    vr = eng.verify_claim("x", [eng.symbolic_equal("1+1", "2"), eng.numeric_agree(2.0, 2.0)])
    assert vr.status == VerificationStatus.PASSED
    assert vr.evidence_level == EvidenceLevel.VERIFIED_COMPUTATION
    vr2 = eng.verify_claim("x", [eng.numeric_agree(1.0, 2.0)])
    assert vr2.status == VerificationStatus.FAILED
    assert vr2.evidence_level == EvidenceLevel.REFUTED
    assert vr2.discrepancy_report  # disagreement triggers investigation text


def test_limiting_case():
    assert eng.limiting_case("v=0", 1.0, 1.0).status == VerificationStatus.PASSED
    assert eng.limiting_case("broken", 1.0, 2.0).status == VerificationStatus.FAILED


def test_quality_gate_blocks_unverified():
    from aimathh.verification.engine import QualityGate

    g = QualityGate().evaluate(
        executed=True, independently_checked=True, units_consistent=True,
        assumptions=["a"], tolerances_reported=True, limiting_cases_ok=True,
        counterexample_searched=None, methods_agree=True, sources_valid=None, reproducible=True)
    assert g["passed"] is True
    assert g["verdict"] == "VERIFIED_COMPUTATION"
    g2 = QualityGate().evaluate(
        executed=False, independently_checked=False, units_consistent=None,
        assumptions=[], tolerances_reported=False, limiting_cases_ok=None,
        counterexample_searched=None, methods_agree=None, sources_valid=None, reproducible=False)
    assert g2["passed"] is False
    assert g2["verdict"] == "UNVERIFIED"


def test_formal_backends_report_honestly():
    from aimathh.verification import formal

    backs = {c.name: c for c in formal.list_backends()}
    assert set(backs) == {"z3", "lean", "coq", "isabelle"}
    # Unavailable backends must say so with install hints, never fake proofs.
    for name, caps in backs.items():
        if not caps.available:
            assert caps.reason and caps.install_hint
