"""Probability, statistics, inference, Monte Carlo (SciPy/NumPy-backed)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats as sstats


def describe(data: list[float]) -> dict[str, Any]:
    x = np.asarray(data, dtype=float)
    if x.size == 0:
        raise ValueError("Empty dataset")
    q = np.quantile(x, [0.0, 0.25, 0.5, 0.75, 1.0])
    return {
        "n": int(x.size),
        "mean": float(np.mean(x)),
        "std": float(np.std(x, ddof=1)) if x.size > 1 else 0.0,
        "min": float(q[0]),
        "q25": float(q[1]),
        "median": float(q[2]),
        "q75": float(q[3]),
        "max": float(q[4]),
        "skew": float(sstats.skew(x)) if x.size > 2 else 0.0,
        "kurtosis": float(sstats.kurtosis(x)) if x.size > 3 else 0.0,
    }


def ttest_1samp(data: list[float], popmean: float = 0.0) -> dict[str, Any]:
    res = sstats.ttest_1samp(np.asarray(data, float), popmean)
    return {"statistic": float(res.statistic), "pvalue": float(res.pvalue), "popmean": popmean}


def ttest_ind(a: list[float], b: list[float]) -> dict[str, Any]:
    res = sstats.ttest_ind(np.asarray(a, float), np.asarray(b, float))
    return {"statistic": float(res.statistic), "pvalue": float(res.pvalue)}


def normaltest(data: list[float]) -> dict[str, Any]:
    res = sstats.normaltest(np.asarray(data, float))
    return {"statistic": float(res.statistic), "pvalue": float(res.pvalue)}


def linregress(x: list[float], y: list[float]) -> dict[str, Any]:
    res = sstats.linregress(np.asarray(x, float), np.asarray(y, float))
    return {
        "slope": float(res.slope),
        "intercept": float(res.intercept),
        "rvalue": float(res.rvalue),
        "r_squared": float(res.rvalue**2),
        "pvalue": float(res.pvalue),
        "stderr": float(res.stderr),
    }


def monte_carlo(
    expr: str,
    variables: list[str],
    distributions: dict[str, dict[str, Any]],
    n: int = 100_000,
    seed: int = 0,
) -> dict[str, Any]:
    """Sample f(variables) under independent input distributions.

    distributions: {name: {"dist": "normal"|"uniform", ...params}}.
    Reports mean/std/quantiles plus a split-half stability check.
    """
    import sympy as sp

    rng = np.random.default_rng(seed)
    e = sp.sympify(expr)
    syms = [sp.Symbol(v) for v in variables]
    f = sp.lambdify(syms, e, "numpy")
    cols: dict[str, np.ndarray] = {}
    for v in variables:
        spec = distributions.get(v, {"dist": "uniform", "low": 0.0, "high": 1.0})
        d = spec.get("dist", "uniform")
        if d == "normal":
            cols[v] = rng.normal(float(spec.get("mean", 0.0)), float(spec.get("std", 1.0)), n)
        elif d == "uniform":
            cols[v] = rng.uniform(float(spec.get("low", 0.0)), float(spec.get("high", 1.0)), n)
        elif d == "lognormal":
            cols[v] = rng.lognormal(float(spec.get("mean", 0.0)), float(spec.get("sigma", 1.0)), n)
        else:
            raise ValueError(f"Unsupported distribution '{d}' for '{v}'")
    vals = np.asarray(f(*[cols[v] for v in variables]), dtype=float)
    half = n // 2
    m1, m2 = float(np.mean(vals[:half])), float(np.mean(vals[half:]))
    return {
        "n": n,
        "seed": seed,
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
        "q05": float(np.quantile(vals, 0.05)),
        "q50": float(np.quantile(vals, 0.50)),
        "q95": float(np.quantile(vals, 0.95)),
        "split_half_means": [m1, m2],
        "split_half_disagreement": abs(m1 - m2),
        "converged": bool(abs(m1 - m2) < 3 * float(np.std(vals)) / np.sqrt(half)),
    }


def bayes_beta_binomial(successes: int, trials: int, a_prior: float = 1.0, b_prior: float = 1.0) -> dict[str, Any]:
    """Conjugate Beta-Binomial posterior with credible interval."""
    a_post, b_post = a_prior + successes, b_prior + trials - successes
    dist = sstats.beta(a_post, b_post)
    return {
        "posterior": {"a": a_post, "b": b_post},
        "mean": float(dist.mean()),
        "map": float((a_post - 1) / (a_post + b_post - 2)) if a_post > 1 and b_post > 1 else float(dist.mean()),
        "ci95": [float(dist.ppf(0.025)), float(dist.ppf(0.975))],
    }
