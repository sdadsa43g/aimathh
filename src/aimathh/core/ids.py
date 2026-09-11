"""Experiment / run / artifact identifiers."""

from __future__ import annotations

import time
import uuid


def new_id(prefix: str = "") -> str:
    """Return a time-sortable unique id like ``exp_20260911T000000_ab12cd34``."""
    ts = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}{ts}_{suffix}" if prefix else f"{ts}_{suffix}"
