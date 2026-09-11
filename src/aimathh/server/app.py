"""AIMathH API server — all harness capabilities behind typed endpoints.

Routes (all under /v1):
  GET  /health
  GET  /models                    GET /models/{name}
  GET  /tools                     POST /tools/{name}/call
  POST /research                  GET /projects  GET /projects/{id}
  POST /execute/python            POST /execute/shell
  POST /math/{symbolic,numeric,linalg,calculus,ode,optimize,stats,transforms,nonlinear}
  POST /physics/{units,constants,dimensional,domains}
  POST /simulations               POST /verify  POST /counterexample
  GET  /artifacts  GET /artifacts/{id}  GET /artifacts/{id}/download
  POST /jobs  GET /jobs  GET /jobs/{id}  DELETE /jobs/{id}
  GET  /memory/{project_id}  POST /memory/{project_id}
  POST /debate  POST /invent
  GET  /observability/stats
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from aimathh.core.config import get_settings
from aimathh.core.logging import configure_logging
from aimathh.models import (
    MockProvider,
    OpenAICompatProvider,
    AnthropicProvider,
    LocalOllamaProvider,
    get_provider,
    list_providers,
    register_provider,
)
from aimathh.orchestrator import get_orchestrator, ResearchRequest

configure_logging()
settings = get_settings()

@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    import aimathh.tools  # noqa: F401  (register built-ins)

    _ensure_providers()
    settings.ensure_dirs()
    yield


app = FastAPI(title="AIMathH Research Harness", version="0.1.0",
              description="Universal Mathematical & Physics AI Research Harness API",
              lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STARTED = time.time()


def _ensure_providers() -> None:
    if "mock" not in list_providers():
        register_provider(MockProvider())
    if settings.openai_api_key and "openai-compat" not in list_providers():
        register_provider(OpenAICompatProvider(base_url=settings.openai_base_url,
                                               api_key=settings.openai_api_key,
                                               model=settings.openai_model))
    if settings.anthropic_api_key and "anthropic" not in list_providers():
        register_provider(AnthropicProvider(base_url=settings.anthropic_base_url,
                                            api_key=settings.anthropic_api_key,
                                            model=settings.anthropic_model))
    if settings.local_model and "local-ollama" not in list_providers():
        register_provider(LocalOllamaProvider(base_url=settings.ollama_base_url, model=settings.local_model))





@app.get("/v1/health")
def health() -> dict[str, Any]:
    import aimathh.tools  # noqa: F401

    _ensure_providers()
    return {"status": "ok", "version": "0.1.0", "uptime_s": time.time() - _STARTED}


# -- models ---------------------------------------------------------------
@app.get("/v1/models")
def models_list() -> dict[str, Any]:
    _ensure_providers()
    out = []
    for name in list_providers():
        out.append(get_provider(name).capabilities().model_dump(mode="json"))
    return {"models": out}


class ChatIn(BaseModel):
    provider: str
    messages: list[dict[str, str]] = Field(default_factory=list)
    system: str = ""
    max_tokens: int = 1024
    temperature: float = 0.2


@app.post("/v1/models/chat")
async def models_chat(body: ChatIn) -> dict[str, Any]:
    from aimathh.models.base import ChatMessage, ModelRequest

    _ensure_providers()
    try:
        provider = get_provider(body.provider)
    except Exception as e:
        raise HTTPException(404, str(e)) from e
    resp = await provider.chat(ModelRequest(
        messages=[ChatMessage(role=m.get("role", "user"), content=m.get("content", "")) for m in body.messages],
        system=body.system, max_tokens=body.max_tokens, temperature=body.temperature))
    return resp.model_dump(mode="json")


# -- tools ------------------------------------------------------------------
@app.get("/v1/tools")
def tools_list() -> dict[str, Any]:
    from aimathh.tools import get_tool_registry

    reg = get_tool_registry()
    return {"tools": [s.model_dump(mode="json") for s in reg.list_specs()], "stats": reg.stats}


class ToolCallIn(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict)
    seed: int | None = None
    experiment_id: str = ""


@app.post("/v1/tools/{name}/call")
async def tools_call(name: str, body: ToolCallIn) -> dict[str, Any]:
    from aimathh.core.errors import HarnessError
    from aimathh.tools import get_tool_registry
    from aimathh.tools.registry import ToolContext

    reg = get_tool_registry()
    try:
        res = await reg.call(name, body.args,
                             _server_tool_context(experiment_id=body.experiment_id, seed=body.seed))
    except HarnessError as e:
        raise HTTPException(400, f"{e.code}: {e}") from e
    return res.model_dump(mode="json")


# -- research ---------------------------------------------------------------
class ResearchIn(BaseModel):
    query: str
    project_id: str = ""
    provider: str = ""
    max_steps: int = 25
    seed: int | None = None


@app.post("/v1/research")
async def research(body: ResearchIn) -> dict[str, Any]:
    orch = get_orchestrator()
    res = await orch.research(ResearchRequest(**body.model_dump()))
    return res.model_dump(mode="json")


@app.get("/v1/projects")
def projects_list() -> dict[str, Any]:
    from aimathh.research import get_research_memory

    return {"projects": get_research_memory().list_projects()}


@app.get("/v1/projects/{project_id}")
def projects_get(project_id: str) -> dict[str, Any]:
    from aimathh.research import get_research_memory

    try:
        return get_research_memory().load_project(project_id).model_dump(mode="json")
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


# -- execute ------------------------------------------------------------------
class ExecIn(BaseModel):
    code: str = ""
    command: str = ""
    timeout_s: int = 120
    seed: int | None = None


@app.post("/v1/execute/python")
async def exec_python(body: ExecIn) -> dict[str, Any]:
    from aimathh.tools import get_tool_registry
    from aimathh.tools.registry import ToolContext

    res = await get_tool_registry().call("python_exec", {"code": body.code, "timeout_s": body.timeout_s},
                                         _server_tool_context(seed=body.seed))
    return res.model_dump(mode="json")


@app.post("/v1/execute/shell")
async def exec_shell(body: ExecIn) -> dict[str, Any]:
    from aimathh.tools import get_tool_registry
    from aimathh.tools.registry import ToolContext

    res = await get_tool_registry().call("shell_exec", {"command": body.command}, _server_tool_context())
    return res.model_dump(mode="json")


# -- math / physics / simulations / verify (thin proxies over tools) ------------
def _server_tool_context(experiment_id: str = "", seed: int | None = None):  # type: ignore[no-untyped-def]
    """Server-side permission policy: operator-controlled via settings."""
    from aimathh.execution.permissions import default_permissions
    from aimathh.tools.registry import ToolContext

    return ToolContext(
        experiment_id=experiment_id,
        seed=seed,
        permissions=default_permissions(network=settings.allow_network, write=True),
    )


async def _tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    from aimathh.core.errors import HarnessError
    from aimathh.tools import get_tool_registry

    try:
        res = await get_tool_registry().call(name, args, _server_tool_context())
    except HarnessError as e:
        raise HTTPException(400, f"{e.code}: {e}") from e
    return res.output


@app.post("/v1/math/symbolic")
async def math_symbolic(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("symbolic", body)


@app.post("/v1/math/numeric")
async def math_numeric(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("numeric", body)


@app.post("/v1/math/linalg")
async def math_linalg(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("linalg", body)


@app.post("/v1/math/calculus")
async def math_calculus(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("calculus_numeric", body)


@app.post("/v1/math/ode")
async def math_ode(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("ode_solve", body)


@app.post("/v1/math/optimize")
async def math_optimize(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("optimize", body)


@app.post("/v1/math/stats")
async def math_stats(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("statistics", body)


@app.post("/v1/math/transforms")
async def math_transforms(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("transforms", body)


@app.post("/v1/math/nonlinear")
async def math_nonlinear(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("nonlinear", body)


@app.post("/v1/physics/units")
async def phys_units(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("units", body)


@app.post("/v1/physics/constants")
async def phys_constants(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("constants", body or {"op": "list"})


@app.post("/v1/physics/dimensional")
async def phys_dimensional(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("dimensional_check", body)


@app.post("/v1/physics/domains")
async def phys_domains(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("physics_domain", body or {"op": "list"})


@app.post("/v1/simulations")
async def simulations(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("simulate", body)


@app.post("/v1/verify")
async def verify(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("verify", body)


@app.post("/v1/counterexample")
async def counterexample(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("counterexample", body)


@app.post("/v1/visualize")
async def visualize(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("visualize", body)


@app.post("/v1/scene3d")
async def scene3d(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("scene3d", body)


@app.post("/v1/literature/search")
async def literature_search(body: dict[str, Any]) -> dict[str, Any]:
    return await _tool("literature_search", body)


# -- artifacts ------------------------------------------------------------------
@app.get("/v1/artifacts")
def artifacts_list(experiment_id: str = "") -> dict[str, Any]:
    from aimathh.artifacts import get_artifact_store

    return {"artifacts": [a.model_dump(mode="json") for a in get_artifact_store().list(experiment_id)]}


@app.get("/v1/artifacts/{artifact_id}")
def artifacts_get(artifact_id: str) -> dict[str, Any]:
    from aimathh.artifacts import get_artifact_store

    try:
        return get_artifact_store().get(artifact_id).model_dump(mode="json")
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/v1/artifacts/{artifact_id}/download")
def artifacts_download(artifact_id: str) -> FileResponse:
    from aimathh.artifacts import get_artifact_store

    try:
        art = get_artifact_store().get(artifact_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return FileResponse(art.path, filename=art.filename, media_type=art.mime)


# -- jobs -------------------------------------------------------------------------
class JobIn(BaseModel):
    kind: str = "simulate"
    name: str = "job"
    args: dict[str, Any] = Field(default_factory=dict)


@app.post("/v1/jobs")
async def jobs_submit(body: JobIn) -> dict[str, Any]:
    from aimathh.execution import get_job_queue

    queue = get_job_queue()

    async def _run(job: Any) -> Any:
        job.checkpoint("started", {"kind": body.kind})
        out = await _tool("simulate" if body.kind == "simulate" else body.kind, body.args)
        job.progress = 1.0
        return out

    job = queue.submit(body.name, _run)
    return job.model_dump(mode="json")


@app.get("/v1/jobs")
def jobs_list() -> dict[str, Any]:
    from aimathh.execution import get_job_queue

    return {"jobs": [j.model_dump(mode="json") for j in get_job_queue().list()]}


@app.get("/v1/jobs/{job_id}")
def jobs_get(job_id: str) -> dict[str, Any]:
    from aimathh.execution import get_job_queue

    job = get_job_queue().get(job_id)
    if job is None:
        raise HTTPException(404, f"Unknown job '{job_id}'")
    return job.model_dump(mode="json")


@app.delete("/v1/jobs/{job_id}")
def jobs_cancel(job_id: str) -> dict[str, Any]:
    from aimathh.execution import get_job_queue

    return {"cancelled": get_job_queue().cancel(job_id)}


# -- memory -------------------------------------------------------------------------
@app.get("/v1/memory/{project_id}")
def memory_recall(project_id: str, kind: str = "", query: str = "") -> dict[str, Any]:
    from aimathh.research import get_research_memory

    return {"records": get_research_memory().recall(project_id, kind, query)}


class MemoryIn(BaseModel):
    kind: str = "note"
    title: str = ""
    body: str = ""


@app.post("/v1/memory/{project_id}")
def memory_remember(project_id: str, body: MemoryIn) -> dict[str, Any]:
    from aimathh.research import get_research_memory

    rid = get_research_memory().remember(project_id, body.kind, body.title, body.body)
    return {"record_id": rid}


# -- debate / invent ---------------------------------------------------------------
class DebateIn(BaseModel):
    question: str
    strategies: dict[str, dict[str, Any]]
    project_id: str = ""
    seed: int | None = None


@app.post("/v1/debate")
async def debate(body: DebateIn) -> dict[str, Any]:
    from aimathh.orchestrator.debate import run_debate

    return (await run_debate(body.question, body.strategies, body.project_id, body.seed)).model_dump(mode="json")


class InventIn(BaseModel):
    problem: str
    constraints: list[str] = Field(default_factory=list)
    concepts: list[dict[str, Any]] = Field(default_factory=list)
    simulations: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/v1/invent")
async def invent(body: InventIn) -> dict[str, Any]:
    from aimathh.orchestrator.invention import run_invention_pipeline

    return (await run_invention_pipeline(body.problem, body.constraints, body.concepts, body.simulations)).model_dump(mode="json")


# -- observability ------------------------------------------------------------------
@app.get("/v1/observability/stats")
def obs_stats() -> dict[str, Any]:
    from aimathh.tools import get_tool_registry

    reg = get_tool_registry()
    return {"uptime_s": time.time() - _STARTED, "tool_stats": reg.stats,
            "models": list_providers()}


def run() -> None:
    import uvicorn

    uvicorn.run("aimathh.server.app:app", host=settings.api_host, port=settings.api_port, reload=False)


# Import tools at module load so /tools works even without startup event (tests).
try:
    import aimathh.tools  # noqa: F401

    _ensure_providers()
except Exception:
    pass
