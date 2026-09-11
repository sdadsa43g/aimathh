"""Example domain plugin: extended optics.

Drop-in pattern for adding a physics domain without touching the harness:
define equations + units + assumptions + references, then register.

Usage:
    from plugins.physics.optics_extended import register
    register()
"""

from aimathh.physics.domains import DomainEquation, DomainPlugin, get_domain_registry


def build() -> DomainPlugin:
    return DomainPlugin(
        id="optics_extended",
        title="Optics (extended example plugin)",
        description="Example out-of-tree domain: diffraction, interference, polarization.",
        equations=[
            DomainEquation(
                name="grating",
                latex=r"d\sin\theta = m\lambda",
                expression="d*sin(theta) = m*lam",
                symbols={"d": "m", "theta": "rad", "m": "dimensionless", "lam": "m"},
                assumptions=["far field", "monochromatic"],
                reference="Hecht, Optics, Ch. 10",
            ),
            DomainEquation(
                name="brewster",
                latex=r"\tan\theta_B = n_2/n_1",
                expression="tan(tB) = n2/n1",
                symbols={"tB": "rad", "n2": "dimensionless", "n1": "dimensionless"},
            ),
            DomainEquation(
                name="airy_disk",
                latex=r"\sin\theta = 1.22\lambda/D",
                expression="sin(theta) = 1.22*lam/D",
                symbols={"theta": "rad", "lam": "m", "D": "m"},
                assumptions=["circular aperture", "far field"],
            ),
        ],
        default_units={"lam": "nm", "theta": "rad"},
        assumptions=["linear optics unless stated"],
        validation_rules=["check dimensions", "check paraxial limit"],
        references=["Hecht, Optics"],
    )


def register() -> DomainPlugin:
    plugin = build()
    get_domain_registry().register(plugin)
    return plugin


if __name__ == "__main__":
    p = register()
    print(f"registered domain '{p.id}' with {len(p.equations)} equations")
