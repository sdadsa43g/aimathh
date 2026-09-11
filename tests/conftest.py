"""Shared fixtures: isolated data dirs, registered tools, seeded contexts."""

import pytest

import aimathh.tools  # noqa: F401  (register built-ins)
from aimathh.tools.registry import ToolContext


@pytest.fixture()
def tool_ctx(tmp_path):
    return ToolContext(run_id="test_run", experiment_id="test_exp", seed=12345)


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    """Point data/artifact/sandbox dirs at tmp to keep the repo clean."""
    from aimathh.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "data_dir", tmp_path / "data")
    monkeypatch.setattr(s, "artifact_dir", tmp_path / "data" / "artifacts")
    monkeypatch.setattr(s, "sandbox_root", tmp_path / "data" / "sandbox")
    monkeypatch.setattr(s, "db_path", tmp_path / "data" / "aimathh.db")
    s.ensure_dirs()
    # Reset singletons that captured old paths
    import aimathh.artifacts.store as art
    import aimathh.execution.sandbox as sbx
    import aimathh.research.memory as mem

    monkeypatch.setattr(art, "_store", None)
    monkeypatch.setattr(sbx, "_sandbox", None)
    monkeypatch.setattr(mem, "_memory", None)
    yield
