"""Counterexample engine: attack universal claims computationally.

Given a predicate P(x) claimed to hold for all x in a domain, the engine tries:
  1. symbolic solving of NOT P(x) (exact counterexamples),
  2. dense + random sampling (including boundaries),
  3. adversarial optimization (minimize the "margin" of P),
  4. interval subdivision for 1-D claims.

A single validated counterexample REFUTES the claim. Failure to find one is
reported as "no counterexample found (bounded search)" — never as proof.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from scipy import optimize

from aimathh.core.logging import get_logger
from aimathh.core.types import CheckOutcome, VerificationStatus

log = get_logger("counterexample")


class CounterexampleEngine:
    def __init__(self, seed: int = 0) -> None:
        self.seed = seed

    # -- main entry ------------------------------------------------------
    def attack(
        self,
        predicate_expr: str,
        variables: list[str],
        bounds: dict[str, list[float]],
        *,
        relation: str = ">=",
        threshold: float = 0.0,
        n_random: int = 20_000,
        n_grid: int = 51,
    ) -> dict[str, Any]:
        """Try to find x with NOT (predicate_expr relation threshold).

        ``predicate_expr`` is a sympy expression in ``variables``; the claim is
        that ``predicate_expr >= threshold`` everywhere in ``bounds``.
        Returns a report dict with status 'refuted' | 'no_counterexample_found'.
        """
        t0 = time.time()
        import sympy as sp

        syms = [sp.Symbol(v) for v in variables]
        expr = sp.sympify(predicate_expr)
        f = sp.lambdify(syms, expr, "numpy")
        lo = np.array([bounds[v][0] for v in variables], float)
        hi = np.array([bounds[v][1] for v in variables], float)

        def margin(x: np.ndarray) -> float:
            val = float(np.asarray(f(*x), dtype=float))
            if relation == ">=":
                return val - threshold
            if relation == "<=":
                return threshold - val
            if relation == "==":
                return -abs(val - threshold)
            raise ValueError(f"Unknown relation '{relation}'")

        attempts: list[str] = []

        # 1. Symbolic attempt: solve margin < 0
        attempts.append("symbolic")
        try:
            target = expr - threshold if relation == ">=" else threshold - expr
            sols = sp.solve(sp.Lt(target, 0), syms, dict=True)
            if sols:
                cand = self._point_from_solution(sols[0], variables, bounds)
                if cand is not None and margin(np.asarray(cand)) < 0:
                    return self._refuted(cand, f, variables, t0, "symbolic", attempts)
        except Exception as e:  # noqa: BLE001
            log.debug("symbolic counterexample attempt failed: %s", e)

        # 2. Grid + boundary sampling
        attempts.append(f"grid({n_grid})+boundary")
        if len(variables) == 1:
            xs = np.linspace(lo[0], hi[0], n_grid)
            for x in xs:
                if margin(np.array([x])) < 0:
                    return self._refuted([float(x)], f, variables, t0, "grid", attempts)
            # boundaries with tight offsets
            for x in [lo[0], hi[0]]:
                for eps in (1e-12, 1e-9, 1e-6, 1e-3):
                    for xx in (x - eps, x + eps):
                        if lo[0] <= xx <= hi[0] and margin(np.array([xx])) < 0:
                            return self._refuted([float(xx)], f, variables, t0, "boundary", attempts)
        else:
            rng = np.random.default_rng(self.seed)
            for _ in range(min(n_grid * 10, 5000)):
                x = rng.uniform(lo, hi)
                if margin(x) < 0:
                    return self._refuted(x.tolist(), f, variables, t0, "grid-random", attempts)

        # 3. Random sampling
        attempts.append(f"random({n_random})")
        rng = np.random.default_rng(self.seed + 1)
        batch = 5000
        for start in range(0, n_random, batch):
            m = min(batch, n_random - start)
            xs = rng.uniform(lo, hi, size=(m, len(variables)))
            vals = np.asarray(f(*[xs[:, i] for i in range(len(variables))]), dtype=float)
            if relation == ">=":
                bad = np.where(vals < threshold)[0]
            elif relation == "<=":
                bad = np.where(vals > threshold)[0]
            else:
                bad = np.where(np.abs(vals - threshold) > 1e-9)[0]
            if bad.size:
                return self._refuted(xs[int(bad[0])].tolist(), f, variables, t0, "random", attempts)

        # 4. Adversarial optimization: minimize margin from many starts
        attempts.append("adversarial-optimization")
        best = {"margin": float("inf"), "x": None}
        rng2 = np.random.default_rng(self.seed + 2)
        starts = [rng2.uniform(lo, hi) for _ in range(20)]
        # include corners
        from itertools import product

        for corner in product(*[(l, h) for l, h in zip(lo, hi)]):
            starts.append(np.array(corner, float))
        for s in starts:
            try:
                res = optimize.minimize(
                    lambda x: float(margin(np.asarray(x))),
                    s,
                    bounds=list(zip(lo.tolist(), hi.tolist())),
                    method="L-BFGS-B",
                    options={"maxiter": 200},
                )
                if float(res.fun) < best["margin"]:
                    best = {"margin": float(res.fun), "x": res.x.tolist()}
                if float(res.fun) < 0:
                    return self._refuted(res.x.tolist(), f, variables, t0, "adversarial", attempts)
            except Exception:  # noqa: BLE001
                continue

        return {
            "status": "no_counterexample_found",
            "claim": f"{predicate_expr} {relation} {threshold} on {bounds}",
            "attempts": attempts,
            "best_margin": best["margin"],
            "best_point": best["x"],
            "note": "Bounded search only — this is NOT a proof of the claim.",
            "duration_s": time.time() - t0,
        }

    def check(self, *args: Any, **kwargs: Any) -> CheckOutcome:
        rep = self.attack(*args, **kwargs)
        if rep["status"] == "refuted":
            return CheckOutcome(
                name="counterexample_search",
                status=VerificationStatus.FAILED,
                detail=f"REFUTED by counterexample {rep['counterexample']} "
                       f"(margin={rep['margin']:.3e}, via {rep['found_via']})",
                evidence=rep,
                duration_s=rep.get("duration_s", 0.0),
            )
        return CheckOutcome(
            name="counterexample_search",
            status=VerificationStatus.PASSED,
            detail=f"No counterexample in bounded search ({', '.join(rep['attempts'])}); "
                   f"best margin {rep['best_margin']:.3e}. NOT a proof.",
            evidence=rep,
            duration_s=rep.get("duration_s", 0.0),
        )

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _point_from_solution(sol: dict, variables: list[str], bounds: dict[str, list[float]]) -> list[float] | None:
        import sympy as sp

        pt: list[float] = []
        for v in variables:
            s = sp.Symbol(v)
            if s not in sol:
                return None
            try:
                val = float(sol[s])
            except (TypeError, ValueError):
                return None
            lo, hi = bounds[v]
            if not (lo <= val <= hi):
                return None
            pt.append(val)
        return pt

    @staticmethod
    def _refuted(x: list[float], f: Any, variables: list[str], t0: float, via: str, attempts: list[str]) -> dict[str, Any]:
        import numpy as np2

        val = float(np2.asarray(f(*x), dtype=float))
        point = {v: float(x[i]) for i, v in enumerate(variables)}
        return {
            "status": "refuted",
            "counterexample": point,
            "predicate_value": val,
            "margin": val,
            "found_via": via,
            "attempts": list(attempts),
            "duration_s": time.time() - t0,
        }


_engine: CounterexampleEngine | None = None


def get_counterexample_engine() -> CounterexampleEngine:
    global _engine
    if _engine is None:
        _engine = CounterexampleEngine()
    return _engine
