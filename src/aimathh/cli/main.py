"""`aimathh` CLI: research, compute, verify, simulate, serve."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


def _cmd_research(args: argparse.Namespace) -> int:
    import aimathh.tools  # noqa: F401
    from aimathh.models import MockProvider, register_provider
    from aimathh.orchestrator import ResearchRequest, get_orchestrator

    async def _run() -> None:
        try:
            register_provider(MockProvider())
        except Exception:
            pass
        orch = get_orchestrator()
        res = await orch.research(ResearchRequest(query=args.query, provider=args.provider or "",
                                                  max_steps=args.max_steps, seed=args.seed))
        if args.json:
            print(res.model_dump_json(indent=2))
        else:
            print(res.answer)
            print(f"\n[{res.label()} | confidence={res.confidence:.2f}]")

    asyncio.run(_run())
    return 0


def _cmd_tool(args: argparse.Namespace) -> int:
    import aimathh.tools  # noqa: F401
    from aimathh.tools import get_tool_registry
    from aimathh.tools.registry import ToolContext

    async def _run() -> None:
        reg = get_tool_registry()
        payload = json.loads(args.args or "{}")
        res = await reg.call(args.name, payload, ToolContext(seed=args.seed))
        print(json.dumps(res.output, indent=2, default=str))

    asyncio.run(_run())
    return 0


def _cmd_tools(_: argparse.Namespace) -> int:
    import aimathh.tools  # noqa: F401
    from aimathh.tools import get_tool_registry

    for spec in get_tool_registry().list_specs():
        print(f"{spec.name:22s} {spec.description[:90]}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    from aimathh.verification import get_verification_engine

    eng = get_verification_engine()
    checks = []
    if args.symbolic:
        a, b = args.symbolic
        checks.append(eng.symbolic_equal(a, b))
    if args.numeric:
        va, vb = (float(x) for x in args.numeric)
        checks.append(eng.numeric_agree(va, vb, tol=args.tol))
    if args.dimensional:
        eq = args.dimensional
        syms = dict(kv.split("=", 1) for kv in (args.symbols or []))
        checks.append(eng.dimensional(eq, syms))
    vr = eng.verify_claim(args.claim or "cli claim", checks)
    print(vr.model_dump_json(indent=2))
    return 0 if vr.status.value == "passed" else 2


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("aimathh.server.app:app", host=args.host, port=args.port, reload=False)
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    import runpy
    from pathlib import Path

    demos = sorted(Path("demos").glob("demo*.py"))
    if args.name == "list":
        for d in demos:
            print(d.name)
        return 0
    target = Path("demos") / (args.name if args.name.endswith(".py") else args.name + ".py")
    if not target.exists():
        print(f"Unknown demo '{args.name}'. Available:", file=sys.stderr)
        for d in demos:
            print(f"  {d.stem}", file=sys.stderr)
        return 1
    runpy.run_path(str(target), run_name="__main__")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aimathh", description="Universal Math & Physics AI Research Harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("research", help="Run a research request through the orchestrator")
    r.add_argument("query")
    r.add_argument("--provider", default="")
    r.add_argument("--max-steps", type=int, default=25)
    r.add_argument("--seed", type=int, default=None)
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=_cmd_research)

    t = sub.add_parser("tool", help="Call a single tool")
    t.add_argument("name")
    t.add_argument("--args", default="{}")
    t.add_argument("--seed", type=int, default=None)
    t.set_defaults(func=_cmd_tool)

    tl = sub.add_parser("tools", help="List tools")
    tl.set_defaults(func=_cmd_tools)

    v = sub.add_parser("verify", help="Run verification checks")
    v.add_argument("--claim", default="")
    v.add_argument("--symbolic", nargs=2, metavar=("A", "B"))
    v.add_argument("--numeric", nargs=2, metavar=("A", "B"))
    v.add_argument("--dimensional", metavar="EQUATION")
    v.add_argument("--symbols", nargs="*", metavar="sym=units")
    v.add_argument("--tol", type=float, default=1e-8)
    v.set_defaults(func=_cmd_verify)

    s = sub.add_parser("serve", help="Start the API server")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(func=_cmd_serve)

    d = sub.add_parser("demo", help="Run a demo (or 'list')")
    d.add_argument("name")
    d.set_defaults(func=_cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
