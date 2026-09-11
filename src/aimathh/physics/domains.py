"""Domain plugin architecture — equations/constants/models per physics field.

A ``DomainPlugin`` is a declarative bundle; solvers/validators live in the
math + verification layers so domains stay auditable data + thin logic.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DomainEquation(BaseModel):
    name: str
    latex: str = ""
    expression: str = ""  # sympy-parseable, "= " separated
    symbols: dict[str, str] = Field(default_factory=dict)  # symbol -> units
    assumptions: list[str] = Field(default_factory=list)
    reference: str = ""


class DomainPlugin(BaseModel):
    id: str
    title: str
    description: str = ""
    equations: list[DomainEquation] = Field(default_factory=list)
    constants: dict[str, str] = Field(default_factory=dict)  # name -> constant symbol
    default_units: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    validation_rules: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    def equation(self, name: str) -> DomainEquation:
        for e in self.equations:
            if e.name == name:
                return e
        raise KeyError(f"Domain '{self.id}' has no equation '{name}'")


class DomainRegistry:
    def __init__(self) -> None:
        self._domains: dict[str, DomainPlugin] = {}

    def register(self, plugin: DomainPlugin) -> None:
        self._domains[plugin.id] = plugin

    def get(self, domain_id: str) -> DomainPlugin:
        if domain_id not in self._domains:
            raise KeyError(f"Unknown physics domain '{domain_id}'. Known: {sorted(self._domains)}")
        return self._domains[domain_id]

    def list(self) -> list[str]:
        return sorted(self._domains)

    def all(self) -> list[DomainPlugin]:
        return [self._domains[k] for k in self.list()]


_registry = DomainRegistry()


def get_domain_registry() -> DomainRegistry:
    return _registry


def _build_builtin_domains() -> None:
    if _registry.list():
        return
    _registry.register(DomainPlugin(
        id="classical_mechanics",
        title="Classical Mechanics",
        description="Newtonian, Lagrangian and Hamiltonian mechanics.",
        equations=[
            DomainEquation(name="newton2", latex=r"F = m a", expression="F = m*a",
                           symbols={"F": "newton", "m": "kg", "a": "m/s^2"}),
            DomainEquation(name="kinetic", latex=r"T = \frac{1}{2} m v^2", expression="T = (1/2)*m*v^2",
                           symbols={"T": "joule", "m": "kg", "v": "m/s"}),
            DomainEquation(name="harmonic_oscillator", latex=r"m\ddot{x} + kx = 0", expression="m*a + k*x = 0",
                           symbols={"m": "kg", "a": "m/s^2", "k": "N/m", "x": "m"}),
            DomainEquation(name="pendulum_small_angle", latex=r"\ddot{\theta} + (g/L)\theta = 0",
                           expression="alpha + (g/L)*theta = 0",
                           symbols={"alpha": "rad/s^2", "g": "m/s^2", "L": "m", "theta": "rad"}),
            DomainEquation(name="gravitation", latex=r"F = G m_1 m_2 / r^2", expression="F = G*m1*m2/r^2",
                           symbols={"F": "newton", "G": "m^3/(kg s^2)", "m1": "kg", "m2": "kg", "r": "m"}),
        ],
        constants={"G": "G", "g": "g_earth"},
        assumptions=["non-relativistic speeds", "inertial frames unless stated"],
        validation_rules=["check dimensions", "check energy conservation for conservative systems"],
        references=["Goldstein, Classical Mechanics", "Taylor, Classical Mechanics"],
    ))
    _registry.register(DomainPlugin(
        id="electromagnetism",
        title="Electromagnetism",
        description="Maxwell theory, circuits, EM waves.",
        equations=[
            DomainEquation(name="coulomb", latex=r"F = k q_1 q_2 / r^2", expression="F = k*q1*q2/r^2",
                           symbols={"F": "newton", "k": "N m^2/C^2", "q1": "C", "q2": "C", "r": "m"}),
            DomainEquation(name="lorentz", latex=r"F = q(E + v \times B)", expression="F = q*(E + v*B)",
                           symbols={"F": "newton", "q": "C", "E": "V/m", "v": "m/s", "B": "tesla"}),
            DomainEquation(name="wave_speed", latex=r"c = 1/\sqrt{\mu_0 \epsilon_0}",
                           expression="c = 1/sqrt(mu0*eps0)",
                           symbols={"c": "m/s", "mu0": "N/A^2", "eps0": "F/m"}),
        ],
        constants={"c": "c", "eps0": "epsilon_0", "mu0": "mu_0", "e": "e"},
        validation_rules=["check dimensions", "check gauge/limiting cases"],
        references=["Griffiths, Introduction to Electrodynamics", "Jackson, Classical Electrodynamics"],
    ))
    _registry.register(DomainPlugin(
        id="thermodynamics",
        title="Thermodynamics & Statistical Mechanics",
        equations=[
            DomainEquation(name="ideal_gas", latex="PV = Nk_BT", expression="P*V = N*kB*T",
                           symbols={"P": "pascal", "V": "m^3", "N": "dimensionless", "kB": "J/K", "T": "kelvin"}),
            DomainEquation(name="first_law", latex=r"dU = \delta Q - \delta W", expression="dU = dQ - dW",
                           symbols={"dU": "joule", "dQ": "joule", "dW": "joule"}),
            DomainEquation(name="boltzmann", latex=r"S = k_B \ln \Omega", expression="S = kB*log(Omega)",
                           symbols={"S": "J/K", "kB": "J/K", "Omega": "dimensionless"}),
            DomainEquation(name="maxwell_boltzmann_speed", latex=r"v_p = \sqrt{2kT/m}",
                           expression="vp = sqrt(2*kB*T/m)",
                           symbols={"vp": "m/s", "kB": "J/K", "T": "kelvin", "m": "kg"}),
        ],
        constants={"kB": "k_B", "R": "R", "NA": "N_A"},
        references=["Schroeder, Thermal Physics", "Pathria, Statistical Mechanics"],
    ))
    _registry.register(DomainPlugin(
        id="quantum_mechanics",
        title="Quantum Mechanics",
        equations=[
            DomainEquation(name="schrodinger_1d", latex=r"i\hbar\partial_t\psi = \hat{H}\psi",
                           expression="E = hbar*omega",
                           symbols={"E": "joule", "hbar": "J s", "omega": "rad/s"}),
            DomainEquation(name="de_broglie", latex=r"\lambda = h/p", expression="lam = h/p",
                           symbols={"lam": "m", "h": "J s", "p": "kg m/s"}),
            DomainEquation(name="uncertainty", latex=r"\Delta x \Delta p \ge \hbar/2",
                           expression="dx*dp = hbar/2",
                           symbols={"dx": "m", "dp": "kg m/s", "hbar": "J s"}),
            DomainEquation(name="hydrogen_ground", latex="E_1 = -13.6 eV", expression="E1 = -13.6*eV",
                           symbols={"E1": "joule", "eV": "joule"}),
        ],
        constants={"hbar": "hbar", "h": "h", "me": "m_e"},
        references=["Griffiths, Introduction to Quantum Mechanics", "Sakurai, Modern Quantum Mechanics"],
    ))
    _registry.register(DomainPlugin(
        id="relativity",
        title="Relativity",
        equations=[
            DomainEquation(name="mass_energy", latex="E = mc^2", expression="E = m*c^2",
                           symbols={"E": "joule", "m": "kg", "c": "m/s"}),
            DomainEquation(name="lorentz_factor", latex=r"\gamma = 1/\sqrt{1-v^2/c^2}",
                           expression="gamma = 1/sqrt(1-v^2/c^2)",
                           symbols={"gamma": "dimensionless", "v": "m/s", "c": "m/s"}),
            DomainEquation(name="schwarzschild_radius", latex="r_s = 2GM/c^2", expression="rs = 2*G*M/c^2",
                           symbols={"rs": "m", "G": "m^3/(kg s^2)", "M": "kg", "c": "m/s"}),
        ],
        constants={"c": "c", "G": "G"},
        references=["Hartle, Gravity", "Carroll, Spacetime and Geometry"],
    ))
    _registry.register(DomainPlugin(
        id="fluid_mechanics",
        title="Fluid Mechanics",
        equations=[
            DomainEquation(name="bernoulli", latex=r"p + \rho v^2/2 + \rho g h = const",
                           expression="p + rho*v^2/2 + rho*g*h = C",
                           symbols={"p": "pascal", "rho": "kg/m^3", "v": "m/s", "g": "m/s^2", "h": "m", "C": "pascal"}),
            DomainEquation(name="navier_stokes_x", latex=r"\rho(\partial_t u + u\partial_x u) = -\partial_x p + \mu\nabla^2 u",
                           expression="rho*(du_dt + u*du_dx) = -dp_dx + mu*d2u",
                           symbols={"rho": "kg/m^3", "du_dt": "m/s^2", "u": "m/s", "du_dx": "1/s",
                                    "dp_dx": "Pa/m", "mu": "Pa s", "d2u": "1/(m s)"}),
            DomainEquation(name="reynolds", latex=r"Re = \rho v L / \mu", expression="Re = rho*v*L/mu",
                           symbols={"Re": "dimensionless", "rho": "kg/m^3", "v": "m/s", "L": "m", "mu": "Pa s"}),
        ],
        references=["Kundu, Fluid Mechanics", "Batchelor, An Introduction to Fluid Dynamics"],
    ))
    _registry.register(DomainPlugin(
        id="waves_optics",
        title="Waves & Optics",
        equations=[
            DomainEquation(name="wave_eq_dispersion", latex=r"\omega = ck", expression="omega = c*k",
                           symbols={"omega": "rad/s", "c": "m/s", "k": "rad/m"}),
            DomainEquation(name="snell", latex=r"n_1\sin\theta_1 = n_2\sin\theta_2",
                           expression="n1*sin(t1) = n2*sin(t2)",
                           symbols={"n1": "dimensionless", "t1": "rad", "n2": "dimensionless", "t2": "rad"}),
            DomainEquation(name="thin_lens", latex="1/f = 1/d_o + 1/d_i", expression="1/f = 1/do + 1/di",
                           symbols={"f": "m", "do": "m", "di": "m"}),
        ],
        references=["Hecht, Optics"],
    ))
    _registry.register(DomainPlugin(
        id="astrophysics",
        title="Astrophysics",
        equations=[
            DomainEquation(name="kepler3", latex=r"T^2 = 4\pi^2 a^3 / GM", expression="T^2 = 4*pi^2*a^3/(G*M)",
                           symbols={"T": "s", "a": "m", "G": "m^3/(kg s^2)", "M": "kg"}),
            DomainEquation(name="stefan_boltzmann", latex=r"L = 4\pi R^2 \sigma T^4",
                           expression="L = 4*pi*R^2*sigma*T^4",
                           symbols={"L": "watt", "R": "m", "sigma": "W/(m^2 K^4)", "T": "kelvin"}),
            DomainEquation(name="hubble", latex="v = H_0 d", expression="v = H0*d",
                           symbols={"v": "m/s", "H0": "1/s", "d": "m"}),
        ],
        constants={"G": "G", "sigma": "sigma_sb"},
        references=["Carroll & Ostlie, Modern Astrophysics"],
    ))


_build_builtin_domains()
