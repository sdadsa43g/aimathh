"""Built-in tool registrations — the model's hands.

Each tool is a thin, schema-validated adapter over a tested engine. Tools do
not contain business logic beyond argument shaping; engines own correctness.
"""

from __future__ import annotations

from typing import Any

from aimathh.execution.permissions import Permission, PermissionSet
from aimathh.tools.registry import ToolContext, tool, validate_required

# ---------------------------------------------------------------- python/shell
@tool(
    "python_exec",
    "Execute Python code inside the isolated sandbox. Returns stdout/stderr/returncode. "
    "Use for custom computation, data analysis, plotting scripts. Sandboxed: no network, "
    "memory/time limits enforced.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source to execute"},
            "timeout_s": {"type": "integer", "default": 120},
            "seed": {"type": "integer"},
            "capture_artifacts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["code"],
    },
    permissions=PermissionSet(allowed={Permission.EXECUTE, Permission.READ, Permission.WRITE}),
    tags=["execution", "code"],
)
def _python_exec(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    validate_required(args, "code")
    from aimathh.execution.sandbox import ExecutionRequest, get_sandbox

    req = ExecutionRequest(
        code=args["code"],
        language="python",
        timeout_s=args.get("timeout_s"),
        seed=args.get("seed", ctx.seed),
        permissions=ctx.permissions,
        capture_artifacts=args.get("capture_artifacts", []),
    )
    res = get_sandbox().run_python(req)
    out: dict[str, Any] = res.model_dump()
    # Persist captured artifacts into the store
    if res.artifacts:
        from aimathh.artifacts import get_artifact_store

        store = get_artifact_store()
        saved = []
        for name, abspath in res.artifacts.items():
            a = store.save_file(abspath, description=f"sandbox output {name}", experiment_id=ctx.experiment_id)
            saved.append(a.model_dump())
        out["saved_artifacts"] = saved
    return out


@tool(
    "shell_exec",
    "Execute a shell command inside the sandbox workdir. Restricted; prefer python_exec.",
    input_schema={
        "type": "object",
        "properties": {"command": {"type": "string"}, "timeout_s": {"type": "integer", "default": 60}},
        "required": ["command"],
    },
    permissions=PermissionSet(allowed={Permission.EXECUTE, Permission.READ}),
    tags=["execution"],
)
def _shell_exec(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    validate_required(args, "command")
    from aimathh.execution.sandbox import ExecutionRequest, get_sandbox

    req = ExecutionRequest(code=args["command"], language="shell",
                           timeout_s=args.get("timeout_s", 60), permissions=ctx.permissions)
    return get_sandbox().run_shell(req).model_dump()


# ------------------------------------------------------------------- symbolic
@tool(
    "symbolic",
    "Symbolic mathematics: simplify/expand/factor/diff/integrate/solve/series/limit/matrix/equals. "
    "Exact computer algebra via SymPy. Always prefer this over hand-derived algebra.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["simplify", "expand", "factor", "diff", "integrate",
                                              "solve", "solve_system", "series", "limit",
                                              "matrix", "equals", "lambdastr"]},
            "expr": {"type": "string"},
            "equations": {"type": "array", "items": {"type": "string"}},
            "other": {"type": "string", "description": "second expression for equals"},
            "var": {"type": "string"},
            "variables": {"type": "array", "items": {"type": "string"}},
            "order": {"type": "integer", "default": 1},
            "a": {"type": "string"},
            "b": {"type": "string"},
            "point": {"type": "number", "default": 0.0},
            "direction": {"type": "string", "default": "+-"},
            "matrices": {"type": "array"},
            "backend": {"type": "string", "default": "numpy"},
        },
        "required": ["op"],
    },
    tags=["math", "symbolic"],
)
def _symbolic(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import symbolic as S

    op = args["op"]
    if op == "simplify":
        return S.simplify_expr(args["expr"], args.get("variables"))
    if op == "expand":
        return S.expand_expr(args["expr"], args.get("variables"))
    if op == "factor":
        return S.factor_expr(args["expr"], args.get("variables"))
    if op == "diff":
        return S.differentiate(args["expr"], args["var"], args.get("order", 1), args.get("variables"))
    if op == "integrate":
        return S.integrate(args["expr"], args["var"], args.get("a"), args.get("b"), args.get("variables"))
    if op == "solve":
        return S.solve_equation(args["expr"], args["var"], args.get("variables"))
    if op == "solve_system":
        return S.solve_system(args["equations"], args["variables"])
    if op == "series":
        return S.series_expand(args["expr"], args["var"], args.get("point", 0.0), args.get("order", 6), args.get("variables"))
    if op == "limit":
        return S.limit_expr(args["expr"], args["var"], args.get("a", "0"), args.get("direction", "+-"), args.get("variables"))
    if op == "matrix":
        return S.matrix_op(args.get("var", "det"), args["matrices"])
    if op == "equals":
        return S.are_symbolically_equal(args["expr"], args["other"], args.get("variables"))
    if op == "lambdastr":
        return {"source": S.to_numeric_function(args["expr"], args["variables"], args.get("backend", "numpy"))}
    raise ValueError(f"Unknown symbolic op '{op}'")


@tool(
    "numeric",
    "Arbitrary-precision numerical evaluation (mpmath): evaluate expressions or constants "
    "at dps decimal digits with an independent higher-precision cross-check.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["evaluate", "constants", "quad"]},
            "expr": {"type": "string"},
            "variables": {"type": "object"},
            "dps": {"type": "integer", "default": 15},
            "var": {"type": "string", "default": "x"},
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["op"],
    },
    tags=["math", "numeric"],
)
def _numeric(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import numeric as N

    op = args["op"]
    if op == "evaluate":
        return N.evaluate(args["expr"], args.get("variables"), args.get("dps", 15))
    if op == "constants":
        return N.constants(args.get("dps", 50))
    if op == "quad":
        return N.quad_high_precision(args["expr"], args.get("var", "x"), args["a"], args["b"], args.get("dps", 30))
    raise ValueError(f"Unknown numeric op '{op}'")


@tool(
    "linalg",
    "Numerical linear algebra: solve/eig/svd/det/inv/qr with residual + conditioning diagnostics.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["solve", "eig", "svd", "det", "inv", "qr"]},
            "a": {"type": "array"},
            "b": {"type": "array"},
        },
        "required": ["op", "a"],
    },
    tags=["math", "linalg"],
)
def _linalg(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import linalg as L

    op = args["op"]
    if op == "solve":
        return L.solve_linear(args["a"], args["b"])
    if op == "eig":
        return L.eig(args["a"])
    if op == "svd":
        return L.svd(args["a"])
    if op == "det":
        return L.det(args["a"])
    if op == "inv":
        return L.inv(args["a"])
    if op == "qr":
        return L.qr(args["a"])
    raise ValueError(f"Unknown linalg op '{op}'")


@tool(
    "calculus_numeric",
    "Numerical calculus: quadrature (with independent Gauss-Legendre check), numerical "
    "derivatives (with step-convergence study), bracketed root finding.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["quad", "dblquad", "derivative", "root"]},
            "expr": {"type": "string"},
            "var": {"type": "string", "default": "x"},
            "a": {"type": "number"},
            "b": {"type": "number"},
            "point": {"type": "number"},
            "order": {"type": "integer", "default": 1},
            "tol": {"type": "number", "default": 1e-10},
        },
        "required": ["op", "expr"],
    },
    tags=["math", "calculus"],
)
def _calculus_numeric(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import calculus as C

    op = args["op"]
    if op == "quad":
        return C.quad(args["expr"], args["a"], args["b"], args.get("var", "x"), args.get("tol", 1e-10))
    if op == "dblquad":
        return C.dblquad(args["expr"], args["a"], args["b"], args.get("point", 0.0), args.get("tol", 1.0))
    if op == "derivative":
        return C.derivative(args["expr"], args["point"], args.get("var", "x"), args.get("order", 1))
    if op == "root":
        return C.find_root(args["expr"], args["a"], args["b"], args.get("var", "x"))
    raise ValueError(f"Unknown calculus op '{op}'")


@tool(
    "ode_solve",
    "Solve ODE initial-value problems with TWO independent integrators (DOP853 + Radau) "
    "and automatic agreement diagnostics. rhs_exprs are sympy strings in t, variables, params.",
    input_schema={
        "type": "object",
        "properties": {
            "rhs_exprs": {"type": "array", "items": {"type": "string"}},
            "variables": {"type": "array", "items": {"type": "string"}},
            "t_span": {"type": "array", "items": {"type": "number"}},
            "y0": {"type": "array", "items": {"type": "number"}},
            "params": {"type": "object"},
            "rtol": {"type": "number", "default": 1e-9},
            "n_points": {"type": "integer", "default": 200},
        },
        "required": ["rhs_exprs", "variables", "t_span", "y0"],
    },
    tags=["math", "ode", "simulation"],
)
def _ode_solve(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import ode as O

    return O.solve_ivp(
        args["rhs_exprs"], args["variables"], args["t_span"], args["y0"],
        params=args.get("params"), rtol=args.get("rtol", 1e-9), n_points=args.get("n_points", 200),
    )


@tool(
    "optimize",
    "Optimization: local minimize (analytic gradient + Nelder-Mead check), global "
    "differential-evolution (dual-annealing check), least_squares, sensitivity analysis.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["minimize", "global", "least_squares", "sensitivity"]},
            "expr": {"type": "string"},
            "exprs": {"type": "array", "items": {"type": "string"}},
            "variables": {"type": "array", "items": {"type": "string"}},
            "x0": {"type": "array", "items": {"type": "number"}},
            "point": {"type": "array", "items": {"type": "number"}},
            "bounds": {"type": "array"},
            "seed": {"type": "integer", "default": 0},
        },
        "required": ["op", "variables"],
    },
    tags=["math", "optimization"],
)
def _optimize(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import optimize as OPT

    op = args["op"]
    if op == "minimize":
        return OPT.minimize(args["expr"], args["variables"], args["x0"], bounds=args.get("bounds"))
    if op == "global":
        return OPT.global_minimize(args["expr"], args["variables"], args["bounds"], args.get("seed", 0))
    if op == "least_squares":
        return OPT.least_squares(args["exprs"], args["variables"], args["x0"])
    if op == "sensitivity":
        return OPT.sensitivity(args["expr"], args["variables"], args["point"])
    raise ValueError(f"Unknown optimize op '{op}'")


@tool(
    "statistics",
    "Statistics: describe/ttest/normaltest/linregress/monte_carlo/beta_binomial. "
    "Monte Carlo includes split-half convergence diagnostics.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["describe", "ttest_1samp", "ttest_ind", "normaltest",
                                              "linregress", "monte_carlo", "beta_binomial"]},
            "data": {"type": "array", "items": {"type": "number"}},
            "data2": {"type": "array", "items": {"type": "number"}},
            "x": {"type": "array", "items": {"type": "number"}},
            "y": {"type": "array", "items": {"type": "number"}},
            "popmean": {"type": "number", "default": 0.0},
            "expr": {"type": "string"},
            "variables": {"type": "array", "items": {"type": "string"}},
            "distributions": {"type": "object"},
            "n": {"type": "integer", "default": 100000},
            "seed": {"type": "integer", "default": 0},
            "successes": {"type": "integer"},
            "trials": {"type": "integer"},
        },
        "required": ["op"],
    },
    tags=["math", "statistics"],
)
def _statistics(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import stats as ST

    op = args["op"]
    if op == "describe":
        return ST.describe(args["data"])
    if op == "ttest_1samp":
        return ST.ttest_1samp(args["data"], args.get("popmean", 0.0))
    if op == "ttest_ind":
        return ST.ttest_ind(args["data"], args["data2"])
    if op == "normaltest":
        return ST.normaltest(args["data"])
    if op == "linregress":
        return ST.linregress(args["x"], args["y"])
    if op == "monte_carlo":
        return ST.monte_carlo(args["expr"], args["variables"], args["distributions"],
                              args.get("n", 100000), args.get("seed", ctx.seed or 0))
    if op == "beta_binomial":
        return ST.bayes_beta_binomial(args["successes"], args["trials"])
    raise ValueError(f"Unknown statistics op '{op}'")


@tool(
    "transforms",
    "Fourier/Laplace: symbolic transforms with roundtrip check, numeric FFT spectra.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["fourier", "laplace", "fft"]},
            "expr": {"type": "string"},
            "signal": {"type": "array", "items": {"type": "number"}},
            "dt": {"type": "number"},
        },
        "required": ["op"],
    },
    tags=["math", "transforms"],
)
def _transforms(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import transforms as T

    if args["op"] == "fourier":
        return T.fourier_symbolic(args["expr"])
    if args["op"] == "laplace":
        return T.laplace_symbolic(args["expr"])
    if args["op"] == "fft":
        return T.fft_spectrum(args["signal"], args["dt"])
    raise ValueError(f"Unknown transforms op '{args['op']}'")


@tool(
    "nonlinear",
    "Nonlinear systems: solve (residual-verified + stability eigenvalues), "
    "fixed-point stability classification, 2D vector-field sampling.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["solve", "stability", "field"]},
            "exprs": {"type": "array", "items": {"type": "string"}},
            "variables": {"type": "array", "items": {"type": "string"}},
            "x0": {"type": "array", "items": {"type": "number"}},
            "point": {"type": "array", "items": {"type": "number"}},
            "params": {"type": "object"},
            "ranges": {"type": "object"},
            "n": {"type": "integer", "default": 20},
        },
        "required": ["op", "variables"],
    },
    tags=["math", "nonlinear", "dynamical"],
)
def _nonlinear(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.math import nonlinear as NL

    if args["op"] == "solve":
        return NL.solve_nonlinear(args["exprs"], args["variables"], args["x0"])
    if args["op"] == "stability":
        return NL.fixed_point_stability(args["exprs"], args["variables"], args["point"], args.get("params"))
    if args["op"] == "field":
        return NL.vector_field(args["exprs"], args["variables"], args["ranges"], args.get("n", 20), args.get("params"))
    raise ValueError(f"Unknown nonlinear op '{args['op']}'")


# ------------------------------------------------------------------- physics
@tool(
    "units",
    "Unit conversion and SI reduction via Pint. Quantities like '3.2 km/s', targets like 'm/s'.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["convert", "to_si", "dimensionality"]},
            "quantity": {"type": "string"},
            "to": {"type": "string"},
        },
        "required": ["op", "quantity"],
    },
    tags=["physics", "units"],
)
def _units(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.physics import units as U

    if args["op"] == "convert":
        return U.convert(args["quantity"], args["to"])
    if args["op"] == "to_si":
        return U.to_si(args["quantity"])
    return {"quantity": args["quantity"], "dimensionality": U.dimensionality(args["quantity"])}


@tool(
    "constants",
    "Look up a physical constant (CODATA via SciPy) or list all. Values carry units + provenance.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}, "op": {"type": "string", "enum": ["get", "list"], "default": "get"}},
        "required": [],
    },
    tags=["physics", "constants"],
)
def _constants(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.physics import constants as C

    if args.get("op", "get") == "list":
        return {"constants": C.list_constants(), "codata": C.CODATA_VERSION}
    return C.get_constant(args["name"])


@tool(
    "dimensional_check",
    "LEVEL-3 verification: check an equation's dimensional consistency. Provide symbol->units "
    "for EVERY symbol ('dimensionless' for pure numbers). Rejects invalid physics.",
    input_schema={
        "type": "object",
        "properties": {
            "equation": {"type": "string", "description": "'lhs = rhs' or bare expression"},
            "symbols": {"type": "object", "description": "symbol -> pint units"},
        },
        "required": ["equation", "symbols"],
    },
    tags=["physics", "verification"],
)
def _dimensional_check(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.physics.dimensional import check_equation

    return check_equation(args["equation"], args["symbols"]).model_dump()


@tool(
    "physics_domain",
    "Browse the physics domain plugins (equations, units, assumptions, references).",
    input_schema={
        "type": "object",
        "properties": {"op": {"type": "string", "enum": ["list", "get"], "default": "list"},
                       "domain": {"type": "string"}},
    },
    tags=["physics"],
)
def _physics_domain(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.physics.domains import get_domain_registry

    reg = get_domain_registry()
    if args.get("op", "list") == "list":
        return {"domains": [{"id": d.id, "title": d.title, "n_equations": len(d.equations)} for d in reg.all()]}
    return reg.get(args["domain"]).model_dump()


# ---------------------------------------------------------------- simulation
@tool(
    "simulate",
    "Run simulations: ODE (with energy diagnostics), 1D heat PDE (with analytic cross-check), "
    "parameter sweeps, Monte Carlo. Returns trajectories + diagnostics + replay info.",
    input_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["ode", "heat_1d", "sweep", "monte_carlo"]},
            "rhs_exprs": {"type": "array", "items": {"type": "string"}},
            "variables": {"type": "array", "items": {"type": "string"}},
            "t_span": {"type": "array", "items": {"type": "number"}},
            "y0": {"type": "array", "items": {"type": "number"}},
            "params": {"type": "object"},
            "energy_expr": {"type": "string"},
            "sweep": {"type": "object"},
            "observable": {"type": "string"},
            "expr": {"type": "string"},
            "distributions": {"type": "object"},
            "n": {"type": "integer"},
            "seed": {"type": "integer"},
            "pde": {"type": "object"},
        },
        "required": ["kind"],
    },
    tags=["simulation"],
)
def _simulate(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.simulation import runner as R

    kind = args["kind"]
    if kind == "ode":
        return R.run_ode_simulation(
            args["rhs_exprs"], args["variables"], args["t_span"], args["y0"],
            params=args.get("params"), energy_expr=args.get("energy_expr"),
            seed=args.get("seed", ctx.seed))
    if kind == "heat_1d":
        return R.run_heat_1d(seed=args.get("seed", ctx.seed), **(args.get("pde") or {}))
    if kind == "sweep":
        return R.run_parameter_sweep(
            args["rhs_exprs"], args["variables"], args["t_span"], args["y0"],
            args["sweep"], params=args.get("params"), observable=args.get("observable"))
    if kind == "monte_carlo":
        return R.run_monte_carlo_simulation(
            args["expr"], args["variables"], args["distributions"],
            args.get("n", 50000), args.get("seed", ctx.seed or 0))
    raise ValueError(f"Unknown simulation kind '{kind}'")


# ------------------------------------------------------------- visualization
@tool(
    "visualize",
    "Build a Plotly figure spec from computed data + save a PNG artifact. Input must be real "
    "data arrays — the tool refuses to plot without data.",
    input_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["line", "scatter", "ode", "phase", "field",
                                                "surface", "histogram", "spectrum"]},
            "title": {"type": "string", "default": ""},
            "x": {"type": "array", "items": {"type": "number"}},
            "y": {"type": "array"},
            "ys": {"type": "object"},
            "variables": {"type": "array", "items": {"type": "string"}},
            "field": {"type": "object"},
            "z": {"type": "array"},
            "values": {"type": "array", "items": {"type": "number"}},
            "freqs": {"type": "array", "items": {"type": "number"}},
            "mags": {"type": "array", "items": {"type": "number"}},
            "save_png": {"type": "boolean", "default": True},
        },
        "required": ["kind"],
    },
    tags=["visualization"],
)
def _visualize(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.visualization import plots as P

    kind = args["kind"]
    title = args.get("title", "")
    if kind == "line":
        fig = P.line_plot(args["x"], args["ys"], title=title)
    elif kind == "scatter":
        fig = P.scatter_plot(args["x"], args["y"], title=title)
    elif kind == "ode":
        fig = P.ode_trajectories_plot(args["x"], args["y"], args["variables"], title=title or "ODE solution")
    elif kind == "phase":
        fig = P.phase_portrait(args["x"], args["y"], title=title)
    elif kind == "field":
        fig = P.vector_field_plot(args["field"], title=title)
    elif kind == "surface":
        fig = P.surface_spec(args["x"], args["y"], args["z"], title=title)
    elif kind == "histogram":
        fig = P.histogram_spec(args["values"], title=title)
    elif kind == "spectrum":
        fig = P.spectrum_plot(args["freqs"], args["mags"], title=title)
    else:
        raise ValueError(f"Unknown plot kind '{kind}'")
    out: dict[str, Any] = {"figure": fig}
    if args.get("save_png", True):
        from aimathh.artifacts import get_artifact_store
        from aimathh.core.ids import new_id as nid
        from aimathh.core.config import get_settings

        settings = get_settings()
        tmp = settings.data_dir / "tmp" / f"{nid('plot_')}.png"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        P.save_matplotlib_png(fig, tmp, title)
        art = get_artifact_store().save_file(tmp, kind="figure", description=title or kind,
                                             experiment_id=ctx.experiment_id)
        out["png_artifact"] = art.model_dump()
    return out


@tool(
    "scene3d",
    "Build a 3D scene-graph spec (surface/trajectory/arrows) for the frontend Three.js viewer.",
    input_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["surface", "trajectory", "arrows3"]},
            "expr": {"type": "string"},
            "exprs": {"type": "array", "items": {"type": "string"}},
            "ranges": {"type": "object"},
            "points": {"type": "array"},
            "n": {"type": "integer", "default": 60},
            "title": {"type": "string", "default": ""},
        },
        "required": ["kind"],
    },
    tags=["visualization", "3d"],
)
def _scene3d(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.visualization import scene3d as S3

    kind = args["kind"]
    if kind == "surface":
        return S3.surface_3d(args["expr"], n=args.get("n", 60), title=args.get("title", "")).model_dump()
    if kind == "trajectory":
        return S3.trajectory_3d(args["points"], title=args.get("title", "")).model_dump()
    if kind == "arrows3":
        return S3.vector_field_3d(args["exprs"], args["ranges"], n=args.get("n", 8),
                                  title=args.get("title", "")).model_dump()
    raise ValueError(f"Unknown scene kind '{kind}'")


# -------------------------------------------------------------- verification
@tool(
    "verify",
    "Run verification checks: symbolic equality, numeric agreement, dimensional consistency, "
    "limiting cases. Returns per-check verdicts + evidence level. Use before presenting results.",
    input_schema={
        "type": "object",
        "properties": {
            "claim": {"type": "string"},
            "checks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": ["symbolic_equal", "numeric_agree",
                                                             "dimensional", "limiting_case"]},
                        "a": {"type": "string"}, "b": {"type": "string"},
                        "value_a": {"type": "number"}, "value_b": {"type": "number"},
                        "tol": {"type": "number", "default": 1e-8},
                        "equation": {"type": "string"}, "symbols": {"type": "object"},
                        "label": {"type": "string"}, "computed": {"type": "number"},
                        "expected": {"type": "number"},
                        "variables": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["kind"],
                },
            },
        },
        "required": ["claim", "checks"],
    },
    tags=["verification"],
)
def _verify(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.verification import get_verification_engine

    eng = get_verification_engine()
    outcomes = []
    for c in args["checks"]:
        k = c["kind"]
        if k == "symbolic_equal":
            outcomes.append(eng.symbolic_equal(c["a"], c["b"], c.get("variables")))
        elif k == "numeric_agree":
            outcomes.append(eng.numeric_agree(c["value_a"], c["value_b"], tol=c.get("tol", 1e-8)))
        elif k == "dimensional":
            outcomes.append(eng.dimensional(c["equation"], c["symbols"]))
        elif k == "limiting_case":
            outcomes.append(eng.limiting_case(c.get("label", "case"), c["computed"], c["expected"],
                                              c.get("tol", 1e-6)))
    return eng.verify_claim(args["claim"], outcomes).model_dump(mode="json")


@tool(
    "counterexample",
    "Attack a universal claim (predicate >= threshold on a box) with symbolic, sampling and "
    "adversarial search. A found point REFUTES the claim; no-find is bounded evidence only.",
    input_schema={
        "type": "object",
        "properties": {
            "predicate": {"type": "string"},
            "variables": {"type": "array", "items": {"type": "string"}},
            "bounds": {"type": "object"},
            "relation": {"type": "string", "default": ">="},
            "threshold": {"type": "number", "default": 0.0},
            "n_random": {"type": "integer", "default": 20000},
        },
        "required": ["predicate", "variables", "bounds"],
    },
    tags=["verification", "counterexample"],
)
def _counterexample(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.verification import get_counterexample_engine

    eng = get_counterexample_engine()
    return eng.attack(args["predicate"], args["variables"], args["bounds"],
                      relation=args.get("relation", ">="), threshold=args.get("threshold", 0.0),
                      n_random=args.get("n_random", 20000))


@tool(
    "formal_status",
    "Report formal-verification backend availability (Lean/Coq/Isabelle/Z3). Level-5 checks "
    "require an available backend; unavailable ones return install hints, never fake proofs.",
    input_schema={"type": "object", "properties": {"backend": {"type": "string"}}},
    tags=["verification", "formal"],
)
def _formal_status(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.verification import formal

    if args.get("backend"):
        return formal.get_backend(args["backend"]).capabilities().model_dump()
    return {"backends": [c.model_dump() for c in formal.list_backends()]}


# ---------------------------------------------------------------- literature
@tool(
    "literature_search",
    "Search scientific literature (arXiv + OpenAlex). Returns real retrieved records with "
    "provenance. NEVER invent citations — only cite what this returns.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 8}},
        "required": ["query"],
    },
    permissions=PermissionSet(allowed={Permission.READ, Permission.EXECUTE, Permission.NETWORK}),
    tags=["research", "literature"],
)
async def _literature_search(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    validate_required(args, "query")
    from aimathh.research import get_literature_client

    cites = await get_literature_client().search(args["query"], args.get("max_results", 8))
    return {"query": args["query"], "count": len(cites), "results": [c.model_dump(mode="json") for c in cites]}


# -------------------------------------------------------------------- memory
@tool(
    "memory",
    "Structured research memory: remember/recall decisions, equations, failures, notes per project.",
    input_schema={
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["remember", "recall"]},
            "project_id": {"type": "string"},
            "kind": {"type": "string", "default": "note"},
            "title": {"type": "string"},
            "body": {"type": "string"},
            "query": {"type": "string", "default": ""},
        },
        "required": ["op", "project_id"],
    },
    tags=["research", "memory"],
)
def _memory(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from aimathh.research import get_research_memory

    mem = get_research_memory()
    if args["op"] == "remember":
        rid = mem.remember(args["project_id"], args.get("kind", "note"), args.get("title", ""), args.get("body", ""))
        return {"record_id": rid}
    return {"records": mem.recall(args["project_id"], args.get("kind", ""), args.get("query", ""))}
