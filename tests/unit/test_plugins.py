"""Out-of-tree plugin pattern: domains register, identities verify."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins"))


def test_optics_plugin_registers_and_checks():
    from physics.optics_extended import register

    p = register()
    assert p.id == "optics_extended"
    from aimathh.physics.dimensional import check_equation

    eq = p.equation("grating")
    assert check_equation(eq.expression, eq.symbols).consistent


def test_special_function_identities_hold():
    import mathematics.special_functions as sf

    rep = sf.check_all()
    assert rep["checked"]
    assert all(r["status"] == "passed" for r in rep["checked"])


def test_dataset_generator_reproducible(tmp_path):
    import datasets.pendulum_csv as pc

    p1 = pc.build(tmp_path / "a.csv")
    p2 = pc.build(tmp_path / "b.csv")
    assert p1.read_text() == p2.read_text()  # seed-pinned
    assert (p1.parent / "manifest.json").exists()
