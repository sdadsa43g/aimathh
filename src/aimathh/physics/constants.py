"""Central scientific constants registry (SciPy CODATA + curated)."""

from __future__ import annotations

from typing import Any

import scipy.constants as sc

CODATA_VERSION = "scipy-builtin (CODATA 2018)"

_CURATED: dict[str, dict[str, Any]] = {
    "c": {"value": sc.c, "unit": "m/s", "name": "speed of light in vacuum", "exact": True},
    "G": {"value": sc.G, "unit": "m^3/(kg s^2)", "name": "Newtonian gravitational constant", "exact": False},
    "h": {"value": sc.h, "unit": "J s", "name": "Planck constant", "exact": True},
    "hbar": {"value": sc.hbar, "unit": "J s", "name": "reduced Planck constant", "exact": True},
    "k_B": {"value": sc.k, "unit": "J/K", "name": "Boltzmann constant", "exact": True},
    "e": {"value": sc.e, "unit": "C", "name": "elementary charge", "exact": True},
    "m_e": {"value": sc.m_e, "unit": "kg", "name": "electron mass", "exact": False},
    "m_p": {"value": sc.m_p, "unit": "kg", "name": "proton mass", "exact": False},
    "m_n": {"value": sc.m_n, "unit": "kg", "name": "neutron mass", "exact": False},
    "N_A": {"value": sc.N_A, "unit": "1/mol", "name": "Avogadro constant", "exact": True},
    "R": {"value": sc.R, "unit": "J/(mol K)", "name": "molar gas constant", "exact": True},
    "epsilon_0": {"value": sc.epsilon_0, "unit": "F/m", "name": "vacuum permittivity", "exact": False},
    "mu_0": {"value": sc.mu_0, "unit": "N/A^2", "name": "vacuum permeability", "exact": False},
    "sigma_sb": {"value": sc.sigma, "unit": "W/(m^2 K^4)", "name": "Stefan-Boltzmann constant", "exact": True},
    "alpha": {"value": sc.alpha, "unit": "dimensionless", "name": "fine-structure constant", "exact": False},
    "g_earth": {"value": 9.80665, "unit": "m/s^2", "name": "standard gravity", "exact": True},
    "au": {"value": sc.au, "unit": "m", "name": "astronomical unit", "exact": True},
    "parsec": {"value": sc.parsec, "unit": "m", "name": "parsec", "exact": True},
    "light_year": {"value": sc.light_year, "unit": "m", "name": "light year", "exact": True},
    "eV_to_J": {"value": sc.electron_volt, "unit": "J", "name": "electron volt in joules", "exact": True},
}


def get_constant(name: str) -> dict[str, Any]:
    if name not in _CURATED:
        # Fall back to scipy.constants attributes (value only, SI assumed)
        if hasattr(sc, name):
            return {"value": float(getattr(sc, name)), "unit": "SI", "name": name, "exact": False,
                    "source": "scipy.constants"}
        raise KeyError(f"Unknown constant '{name}'. Known: {sorted(_CURATED)}")
    out = dict(_CURATED[name])
    out["source"] = "scipy.constants/CODATA"
    out["codata"] = CODATA_VERSION
    return out


def list_constants() -> list[dict[str, Any]]:
    return [{"symbol": k, **v} for k, v in sorted(_CURATED.items())]
