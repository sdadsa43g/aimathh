"""Demo 8 — Invention Mode: candidate concept -> model -> simulate -> report.

Problem: keep a small off-grid enclosure warm overnight using only daytime sun.
The pipeline scores candidate concepts, thermally simulates the winner, probes
failure modes, and writes a structured research report artifact. It never
claims the invention "works" — it produces a validation plan instead.
"""

import asyncio
from pathlib import Path

import aimathh.tools  # noqa: F401
from aimathh.artifacts import get_artifact_store
from aimathh.orchestrator.invention import run_invention_pipeline


async def _run() -> None:
    print("=" * 72)
    print("DEMO 8: invention pipeline — solar overnight warmth")
    print("=" * 72)
    brief = await run_invention_pipeline(
        problem="Keep a 2 m³ insulated enclosure above 12°C overnight (8h, ambient 0°C) using only daytime solar gain.",
        constraints=["no external power overnight", "low cost", "passive operation"],
        candidate_concepts=[
            {"name": "water thermal mass",
             "mechanism": "200 L water barrel absorbs solar heat by day, releases it at night.",
             "addresses": ["no external power overnight", "passive operation", "low cost"],
             "equations": ["dT/dt = -k(T-T_amb) + Q_solar(t)/C", "C = m*c_p"],
             "predictions": ["Overnight temperature drop < 6 K given R-10 insulation."],
             "unknowns": ["Actual solar gain on cloudy days", "Stratification losses"],
             "expected_performance": "Holds >= 12°C for 8h if charged to >= 22°C.",
             "validation_plan": ["Charge barrel to 25°C, log overnight decay",
                                 "Fit k against the lumped model", "Repeat on cloudy-day charge"]},
            {"name": "phase-change panels",
             "mechanism": "Paraffin PCM panels melt by day, solidify at night at 18°C.",
             "addresses": ["no external power overnight", "passive operation"],
             "equations": ["Q = m*L_fusion + m*c*dT"],
             "predictions": ["Tighter temperature band than water."],
             "unknowns": ["PCM cost", "cycling lifetime"],
             "expected_performance": "Unknown — needs material data.",
             "validation_plan": ["DSC test of candidate paraffin", "Prototype panel cycling"]},
        ],
        simulations=[{
            # Lumped thermal model of the water-barrel concept, 8h night.
            "kind": "ode",
            "rhs_exprs": ["-k*(T-Tamb)/C"],
            "variables": ["T"],
            "t_span": [0, 8 * 3600],
            "y0": [22.0 + 273.15],
            "params": {"k": 2.5, "Tamb": 273.15, "C": 200 * 4186.0},
        }],
    )
    print(f"\nSelected concept: {brief.selected_concept}")
    print(f"Mechanism: {brief.mechanism}")
    print(f"Simulations run: {len(brief.simulations)}")
    for s in brief.simulations:
        print(f"  - {s.get('summary', s.get('error'))}")
    print(f"Failure-mode probes: {brief.failure_modes}")
    print(f"Verdict: {brief.verdict}")

    report = "\n".join([
        "# Invention Brief — Solar Overnight Warmth", "",
        f"**Selected concept:** {brief.selected_concept}", "",
        "## Mechanism", brief.mechanism, "",
        "## Governing equations",
        *[f"- `{e}`" for e in brief.equations], "",
        "## Predictions",
        *[f"- {p}" for p in brief.predictions], "",
        "## Simulations",
        *[f"- {s}" for s in brief.simulations], "",
        "## Failure modes / critic findings",
        *[f"- {f}" for f in brief.failure_modes], "",
        "## Unknowns",
        *[f"- {u}" for u in brief.unknowns], "",
        "## Validation plan",
        *[f"{i+1}. {v}" for i, v in enumerate(brief.validation_plan)], "",
        f"**Verdict:** {brief.verdict}", "",
        "> Status: CANDIDATE. No claim of a working invention is made herein.",
    ])
    out = Path("data/demo8_invention_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    get_artifact_store().save_file(out, kind="report", description="Invention brief (Demo 8)")
    print(f"\nWrote {out}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
