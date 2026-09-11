"""Numerical linear algebra (NumPy/SciPy-backed)."""

from __future__ import annotations

from typing import Any

import numpy as np


def _mat(m: list[list[float]]) -> np.ndarray:
    return np.asarray(m, dtype=float)


def solve_linear(a: list[list[float]], b: list[float]) -> dict[str, Any]:
    A, bv = _mat(a), np.asarray(b, dtype=float)
    try:
        x = np.linalg.solve(A, bv)
        method = "solve"
    except np.linalg.LinAlgError:
        x, *_ = np.linalg.lstsq(A, bv, rcond=None)
        method = "lstsq(fallback: singular)"
    residual = float(np.linalg.norm(A @ x - bv))
    cond = float(np.linalg.cond(A)) if A.shape[0] == A.shape[1] else float("nan")
    return {
        "x": x.tolist(),
        "method": method,
        "residual_norm": residual,
        "condition_number": cond,
        "well_conditioned": bool(cond < 1e12) if cond == cond else False,
    }


def eig(a: list[list[float]]) -> dict[str, Any]:
    A = _mat(a)
    vals, vecs = np.linalg.eig(A)
    # Residual check ||A v - λ v||
    res = [float(np.linalg.norm(A @ vecs[:, i] - vals[i] * vecs[:, i])) for i in range(len(vals))]
    out_vals = [{"re": float(v.real), "im": float(v.imag)} for v in vals]
    return {"eigenvalues": out_vals, "max_residual": max(res) if res else 0.0, "residuals": res}


def svd(a: list[list[float]]) -> dict[str, Any]:
    A = _mat(a)
    U, s, Vt = np.linalg.svd(A)
    recon = (U * s) @ Vt
    err = float(np.linalg.norm(A - recon))
    return {"singular_values": s.tolist(), "reconstruction_error": err, "rank": int(np.sum(s > s.max() * 1e-12)) if s.size else 0}


def det(a: list[list[float]]) -> dict[str, Any]:
    A = _mat(a)
    sign, logdet = np.linalg.slogdet(A)
    return {"det": float(sign * np.exp(logdet)) if np.isfinite(logdet) else 0.0, "logdet": float(logdet), "sign": float(sign)}


def inv(a: list[list[float]]) -> dict[str, Any]:
    A = _mat(a)
    Ai = np.linalg.inv(A)
    err = float(np.linalg.norm(A @ Ai - np.eye(A.shape[0])))
    return {"inv": Ai.tolist(), "identity_error": err, "condition_number": float(np.linalg.cond(A))}


def qr(a: list[list[float]]) -> dict[str, Any]:
    A = _mat(a)
    Q, R = np.linalg.qr(A)
    err = float(np.linalg.norm(Q @ R - A))
    orth = float(np.linalg.norm(Q.T @ Q - np.eye(Q.shape[1])))
    return {"reconstruction_error": err, "orthogonality_error": orth}
