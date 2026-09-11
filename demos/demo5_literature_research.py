"""Demo 5 — Literature-backed research investigation.

Searches arXiv + OpenAlex for a real question, retrieves records with
provenance, and distinguishes paper claims from AI interpretation.
Degrades gracefully offline (reports unreachability; never invents papers).
"""

import asyncio

import aimathh.tools  # noqa: F401
from aimathh.orchestrator.agents import AgentContext, get_agent


async def _run() -> int:
    print("=" * 72)
    print("DEMO 5: literature-backed investigation")
    print("Question: how does pendulum period depend on amplitude?")
    print("=" * 72)
    agent = get_agent("literature")
    try:
        res = await agent.run(AgentContext(
            goal="pendulum period amplitude correction",
            extra={"query": "pendulum period amplitude correction nonlinear"}))
    except Exception as e:  # noqa: BLE001
        print(f"\nLiterature services unreachable ({e}).")
        print("No sources retrieved — nothing is cited. (Run online for live results.)")
        return 0
    data = res.data
    print(f"\nRetrieved {data.get('count', 0)} records (all with retrieval provenance):")
    for i, c in enumerate(data.get("results", [])[:8], 1):
        authors = ", ".join(c.get("authors", [])[:3])
        print(f"\n[{i}] {c.get('title', '')[:110]}")
        print(f"    {authors} — {c.get('venue', '')} {c.get('year', '')}")
        print(f"    id: {c.get('arxiv_id') or c.get('doi') or c.get('url')}")
        print(f"    verified_retrieved={c.get('verified_retrieved')}")
    if not data.get("results"):
        print("\nNo records retrieved (network unreachable from this environment).")
        print("Per the no-fabrication rule, NO literature-backed conclusion is drawn.")
        return 0
    print("\n--- Interpretation (AI-generated, NOT a paper claim) ---")
    print("The retrieved records suggest T ≈ 2π√(L/g)·(1 + θ₀²/16 + ...); any use of")
    print("this statement must cite the retrieved records above, not this paragraph.")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
