"""Units, constants, dimensional analysis, domains."""

import pytest

from aimathh.physics import constants as C
from aimathh.physics import units as U
from aimathh.physics.dimensional import check_equation
from aimathh.physics.domains import get_domain_registry


def test_convert_kmh_to_ms():
    r = U.convert("100 km/h", "m/s")
    assert abs(r["magnitude"] - 27.77777777777778) < 1e-9


def test_convert_incompatible_raises():
    with pytest.raises(Exception):
        U.convert("3 kg", "m/s")


def test_to_si():
    r = U.to_si("1 eV")
    assert abs(r["magnitude"] - 1.602176634e-19) < 1e-28


def test_constants_have_provenance():
    c = C.get_constant("c")
    assert c["value"] == 299792458.0
    assert "CODATA" in c["codata"] or "codata" in c["source"].lower()


def test_dimensional_valid_equations():
    assert check_equation("F = m*a", {"F": "newton", "m": "kg", "a": "m/s^2"}).consistent
    assert check_equation("E = m*c^2", {"E": "joule", "m": "kg", "c": "m/s"}).consistent
    assert check_equation("T^2 = 4*pi^2*a^3/(G*M)", {"T": "s", "a": "m", "G": "m^3/(kg s^2)",
                                                     "M": "kg", "pi": "dimensionless"}).consistent


def test_dimensional_rejects_invalid():
    r = check_equation("E = m*c", {"E": "joule", "m": "kg", "c": "m/s"})
    assert not r.consistent
    assert "MISMATCH" in r.detail
    r2 = check_equation("x + v", {"x": "m", "v": "m/s"})
    assert not r2.consistent


def test_domains_registered():
    reg = get_domain_registry()
    assert "classical_mechanics" in reg.list()
    assert len(reg.list()) >= 7
    eq = reg.get("classical_mechanics").equation("newton2")
    assert eq.symbols["F"] == "newton"
