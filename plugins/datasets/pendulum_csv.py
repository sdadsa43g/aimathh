"""Example dataset plugin: synthetic pendulum measurements with provenance.

Real dataset plugins fetch from a pinned URL + checksum and land in
data/datasets/<name>/ with a manifest. This example *generates* its data
with a fixed seed so the repo stays self-contained; the manifest records
exactly how, so it is reproducible rather than fabricated.
"""

from pathlib import Path

import numpy as np

MANIFEST = {
    "name": "pendulum_measurements_v1",
    "description": "Synthetic small-angle pendulum period measurements (seed-pinned).",
    "seed": 42,
    "n": 200,
    "columns": ["length_m", "period_s", "amplitude_deg"],
    "generator": "plugins/datasets/pendulum_csv.py",
}


def build(path: str | Path = "data/datasets/pendulum_measurements_v1/measurements.csv") -> Path:
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(MANIFEST["seed"])
    L = rng.uniform(0.2, 2.0, MANIFEST["n"])
    amp = rng.uniform(2.0, 8.0, MANIFEST["n"])
    g = 9.80665
    T0 = 2 * np.pi * np.sqrt(L / g)
    T = T0 * (1 + np.radians(amp) ** 2 / 16) + rng.normal(0, 0.002, MANIFEST["n"])
    np.savetxt(path, np.column_stack([L, T, amp]), delimiter=",",
               header=",".join(MANIFEST["columns"]), comments="")
    (path.parent / "manifest.json").write_text(json.dumps(MANIFEST, indent=2))
    return path


if __name__ == "__main__":
    print("wrote", build())
