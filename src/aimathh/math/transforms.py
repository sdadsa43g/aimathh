"""Fourier / Laplace analysis (symbolic + numeric routes)."""

from __future__ import annotations

from typing import Any

import numpy as np


def fourier_symbolic(expr: str, var: str = "t", freq: str = "w") -> dict[str, Any]:
    import sympy as sp

    t, w = sp.Symbol(var), sp.Symbol(freq)
    e = sp.sympify(expr)
    F = sp.fourier_transform(e, t, w)
    unevaluated = isinstance(F, sp.Integral) or "FourierTransform" in str(type(F))
    out: dict[str, Any] = {"transform": str(F), "latex": sp.latex(F), "unevaluated": bool(unevaluated)}
    if not unevaluated:
        inv = sp.inverse_fourier_transform(F, w, t)
        out["roundtrip"] = str(sp.simplify(inv - e))
        out["roundtrip_is_zero"] = bool(sp.simplify(inv - e) == 0)
    return out


def laplace_symbolic(expr: str, var: str = "t", svar: str = "s") -> dict[str, Any]:
    import sympy as sp

    t, s = sp.Symbol(var), sp.Symbol(svar)
    e = sp.sympify(expr)
    F = sp.laplace_transform(e, t, s, noconds=False)
    return {"transform": str(F[0]), "convergence": str(F[1]), "latex": sp.latex(F[0])}


def fft_spectrum(signal: list[float], dt: float) -> dict[str, Any]:
    x = np.asarray(signal, dtype=float)
    if x.size < 8:
        raise ValueError("Need >= 8 samples for a spectrum")
    windowed = x - np.mean(x)
    spec = np.fft.rfft(windowed)
    freqs = np.fft.rfftfreq(x.size, dt)
    mags = np.abs(spec) / x.size
    peak = int(np.argmax(mags[1:]) + 1) if mags.size > 1 else 0
    return {
        "freqs": freqs.tolist(),
        "magnitudes": mags.tolist(),
        "peak_freq": float(freqs[peak]),
        "peak_magnitude": float(mags[peak]),
        "n": int(x.size),
        "dt": dt,
    }
