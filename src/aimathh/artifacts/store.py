"""Content-addressed artifact store with manifests."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id


class Artifact(BaseModel):
    id: str = ""
    kind: str = ""
    filename: str = ""
    path: str = ""
    mime: str = ""
    size_bytes: int = 0
    sha256: str = ""
    description: str = ""
    experiment_id: str = ""
    created_at: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, data: bytes, filename: str, *, kind: str = "", description: str = "",
                   experiment_id: str = "", meta: dict[str, Any] | None = None) -> Artifact:
        aid = new_id("art_")
        dest = self.root / aid / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self._record(dest, filename, kind=kind, description=description,
                            experiment_id=experiment_id, meta=meta or {})

    def save_text(self, text: str, filename: str, **kw: Any) -> Artifact:
        return self.save_bytes(text.encode("utf-8"), filename, **kw)

    def save_json(self, obj: Any, filename: str, **kw: Any) -> Artifact:
        return self.save_text(json.dumps(obj, indent=2, default=str), filename, **kw)

    def save_file(self, src: Path | str, **kw: Any) -> Artifact:
        src = Path(src)
        return self.save_bytes(src.read_bytes(), src.name, **kw)

    def get(self, artifact_id: str) -> Artifact:
        manifest = self.root / artifact_id / "manifest.json"
        if not manifest.exists():
            # Fall back: find single-file dir
            d = self.root / artifact_id
            if d.is_dir():
                files = [p for p in d.iterdir() if p.is_file()]
                if files:
                    return self._record(files[0], files[0].name)
            raise KeyError(f"Unknown artifact '{artifact_id}'")
        return Artifact.model_validate_json(manifest.read_text())

    def list(self, experiment_id: str = "") -> list[Artifact]:
        out: list[Artifact] = []
        for manifest in sorted(self.root.glob("*/manifest.json")):
            try:
                a = Artifact.model_validate_json(manifest.read_text())
            except Exception:
                continue
            if experiment_id and a.experiment_id != experiment_id:
                continue
            out.append(a)
        return sorted(out, key=lambda a: a.created_at, reverse=True)

    def _record(self, dest: Path, filename: str, *, kind: str, description: str,
                experiment_id: str, meta: dict[str, Any]) -> Artifact:
        blob = dest.read_bytes()
        mime, _ = mimetypes.guess_type(filename)
        art = Artifact(
            id=dest.parent.name,
            kind=kind or _kind_of(filename),
            filename=filename,
            path=str(dest),
            mime=mime or "application/octet-stream",
            size_bytes=len(blob),
            sha256=hashlib.sha256(blob).hexdigest(),
            description=description,
            experiment_id=experiment_id,
            created_at=time.time(),
            meta=meta,
        )
        (dest.parent / "manifest.json").write_text(art.model_dump_json(indent=2))
        return art


def _kind_of(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return {
        "py": "code", "ipynb": "notebook", "csv": "data", "json": "data",
        "parquet": "data", "npz": "data", "svg": "figure", "png": "figure",
        "html": "report", "md": "report", "tex": "report", "pdf": "report",
        "webm": "animation", "mp4": "animation", "glb": "scene3d",
        "stl": "geometry", "vtk": "geometry",
    }.get(ext, ext or "file")


_store: ArtifactStore | None = None


def get_artifact_store() -> ArtifactStore:
    global _store
    if _store is None:
        from aimathh.core.config import get_settings

        settings = get_settings()
        settings.ensure_dirs()
        _store = ArtifactStore(settings.artifact_dir)
    return _store
