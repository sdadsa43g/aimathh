"""Numerical linear algebra with residual diagnostics."""

from aimathh.math import linalg as L


def test_solve():
    r = L.solve_linear([[2, 1], [1, 3]], [5, 7])
    assert abs(r["x"][0] - 1.6) < 1e-12
    assert r["residual_norm"] < 1e-12
    assert r["well_conditioned"] is True


def test_eig_residual():
    r = L.eig([[2, 0], [0, 3]])
    assert r["max_residual"] < 1e-12
    vals = sorted(v["re"] for v in r["eigenvalues"])
    assert abs(vals[0] - 2.0) < 1e-12 and abs(vals[1] - 3.0) < 1e-12


def test_svd_reconstruction():
    r = L.svd([[1, 2], [3, 4]])
    assert r["reconstruction_error"] < 1e-12
    assert r["rank"] == 2


def test_inv_identity():
    r = L.inv([[4, 7], [2, 6]])
    assert r["identity_error"] < 1e-12


def test_det():
    assert abs(L.det([[1, 2], [3, 4]])["det"] + 2.0) < 1e-12


def test_qr():
    r = L.qr([[1, 1], [1, -1]])
    assert r["reconstruction_error"] < 1e-12
    assert r["orthogonality_error"] < 1e-12
