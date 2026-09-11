"""Structured research memory (SQLite-backed, no giant text prompts).

Stores projects, decisions, equations, failed/successful approaches,
artifacts and citations with explicit retrieval — the orchestrator pulls
only what the current subtask needs.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from aimathh.core.ids import new_id
from aimathh.research.models import ResearchProject


class ResearchMemory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, data TEXT, updated_at REAL);
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, project_id TEXT, kind TEXT, title TEXT,
                    body TEXT, tags TEXT, created_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_records_project ON records(project_id);
                CREATE INDEX IF NOT EXISTS idx_records_kind ON records(kind);
                """
            )

    # -- projects ---------------------------------------------------------
    def save_project(self, project: ResearchProject) -> None:
        project.updated_at = time.time()
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO projects (id, data, updated_at) VALUES (?, ?, ?)",
                (project.id, project.model_dump_json(), project.updated_at),
            )

    def load_project(self, project_id: str) -> ResearchProject:
        with self._connect() as con:
            row = con.execute("SELECT data FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown project '{project_id}'")
        return ResearchProject.model_validate_json(row["data"])

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute("SELECT id, data, updated_at FROM projects ORDER BY updated_at DESC").fetchall()
        out = []
        for r in rows:
            p = ResearchProject.model_validate_json(r["data"])
            out.append({"id": p.id, "title": p.title, "goal": p.goal[:200], "updated_at": r["updated_at"],
                        "n_tasks": len(p.tasks), "n_experiments": len(p.experiments)})
        return out

    # -- structured records ------------------------------------------------
    def remember(self, project_id: str, kind: str, title: str, body: str, tags: list[str] | None = None) -> str:
        rid = new_id("mem_")
        with self._connect() as con:
            con.execute(
                "INSERT INTO records (id, project_id, kind, title, body, tags, created_at) VALUES (?,?,?,?,?,?,?)",
                (rid, project_id, kind, title, body, json.dumps(tags or []), time.time()),
            )
        return rid

    def recall(self, project_id: str, kind: str = "", query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as con:
            if kind:
                rows = con.execute(
                    "SELECT * FROM records WHERE project_id=? AND kind=? ORDER BY created_at DESC LIMIT ?",
                    (project_id, kind, limit),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM records WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                    (project_id, limit),
                ).fetchall()
        out = [dict(r) for r in rows]
        if query:
            q = query.lower()
            out = [r for r in out if q in (r["title"] + " " + r["body"]).lower()]
        return out

    def record_decision(self, project_id: str, decision: str, rationale: str) -> str:
        return self.remember(project_id, "decision", decision, rationale)

    def record_failure(self, project_id: str, approach: str, reason: str) -> str:
        return self.remember(project_id, "failed_approach", approach, reason, tags=["failure"])

    def record_equation(self, project_id: str, name: str, latex: str, status: str = "unverified") -> str:
        return self.remember(project_id, "equation", name, f"{latex}\nstatus: {status}")


_memory: ResearchMemory | None = None


def get_research_memory() -> ResearchMemory:
    global _memory
    if _memory is None:
        from aimathh.core.config import get_settings

        settings = get_settings()
        settings.ensure_dirs()
        _memory = ResearchMemory(settings.db_path)
    return _memory
