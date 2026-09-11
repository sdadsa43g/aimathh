"""API surface: typed endpoints respond with schemas."""

from fastapi.testclient import TestClient

from aimathh.server.app import app

client = TestClient(app)


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_tools_list():
    r = client.get("/v1/tools")
    names = {t["name"] for t in r.json()["tools"]}
    assert {"python_exec", "symbolic", "verify", "simulate", "dimensional_check"} <= names


def test_symbolic_endpoint():
    r = client.post("/v1/math/symbolic", json={"op": "simplify", "expr": "2+2"})
    assert r.json()["simplified"] == "4"


def test_dimensional_endpoint_rejects():
    r = client.post("/v1/physics/dimensional",
                    json={"equation": "E = m*c", "symbols": {"E": "joule", "m": "kg", "c": "m/s"}})
    assert r.json()["consistent"] is False


def test_verify_endpoint():
    r = client.post("/v1/verify", json={
        "claim": "1+1=2",
        "checks": [{"kind": "symbolic_equal", "a": "1+1", "b": "2"},
                   {"kind": "numeric_agree", "value_a": 2.0, "value_b": 2.0}]})
    body = r.json()
    assert body["status"] == "passed"
    assert body["evidence_level"] == "verified_computation"


def test_exec_endpoint():
    r = client.post("/v1/execute/python", json={"code": "print(40+2)"})
    assert "42" in r.json()["output"]["stdout"]


def test_models_list():
    r = client.get("/v1/models")
    assert any(m["provider"] == "mock" for m in r.json()["models"])


def test_ode_endpoint():
    r = client.post("/v1/math/ode", json={"rhs_exprs": ["-y"], "variables": ["y"],
                                          "t_span": [0, 1], "y0": [1.0], "n_points": 20})
    assert r.json()["agree"] is True


def test_research_endpoint_returns_structured():
    r = client.post("/v1/research", json={"query": "simplify x+x", "max_steps": 2})
    body = r.json()
    assert "answer" in body and "verification" in body and "computations" in body
