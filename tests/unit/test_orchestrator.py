"""Orchestrator, agents, debate, invention, memory, artifacts."""

from aimathh.artifacts import get_artifact_store
from aimathh.orchestrator import get_orchestrator, ResearchRequest
from aimathh.orchestrator.agents import AgentContext, get_agent, list_agents
from aimathh.orchestrator.debate import run_debate
from aimathh.orchestrator.invention import run_invention_pipeline
from aimathh.research import get_research_memory


async def test_agents_registered():
    names = {a["name"] for a in list_agents()}
    assert {"mathematics", "physics", "verification", "simulation", "critic", "coding"} <= names


async def test_math_agent_simplifies():
    res = await get_agent("mathematics").run(AgentContext(goal="t", extra={"task": {"kind": "simplify", "expr": "2+2"}}))
    assert "4" in res.summary or res.computations


async def test_physics_agent_flags_bad_equation():
    res = await get_agent("physics").run(AgentContext(
        goal="t", extra={"task": {"equation": "E = m*c", "symbols": {"E": "joule", "m": "kg", "c": "m/s"}}}))
    assert "MISMATCH" in res.summary


async def test_orchestrator_heuristic_run_is_unverified_not_fake():
    orch = get_orchestrator()
    res = await orch.research(ResearchRequest(query="What is 2+2?", max_steps=3))
    # The heuristic plan has no real verification step -> must stay UNVERIFIED.
    assert res.verification.evidence_level.value == "unverified"
    assert res.answer  # but still produces a structured answer


async def test_debate_agreement_and_conflict():
    v = await run_debate("q", {
        "a": {"agent": "mathematics", "task": {"kind": "evaluate", "expr": "2+2", "dps": 15}},
        "b": {"agent": "mathematics", "task": {"kind": "simplify", "expr": "2+2"}},
    })
    assert v.verdict  # completes; scalar comparison only when data carries scalars
    assert v.evidence_level.value in ("verified_computation", "heuristic", "unverified")


async def test_invention_pipeline_never_claims_success():
    brief = await run_invention_pipeline(
        "cool a room", ["low power"], [{"name": "fan", "mechanism": "moves air",
                                        "equations": ["P = F*v"], "simulations": []}])
    assert brief.selected_concept == "fan"
    assert "CANDIDATE" in brief.verdict
    assert "not a validated invention" in brief.verdict
    assert brief.validation_plan


async def test_memory_roundtrip():
    mem = get_research_memory()
    from aimathh.research.models import ResearchProject

    p = ResearchProject.create("t", "g")
    mem.save_project(p)
    assert mem.load_project(p.id).title == "t"
    mem.remember(p.id, "decision", "use RK45", "stiff check pending")
    assert mem.recall(p.id, "decision")[0]["title"] == "use RK45"


async def test_artifacts_roundtrip():
    store = get_artifact_store()
    a = store.save_text("# hello", "note.md", kind="report", description="t")
    assert store.get(a.id).sha256 == a.sha256
    assert len(store.list()) >= 1
