"""Adapter: UNTOUCHED organizer Colab generator output -> scenario dict that
normalize() accepts. Every conversion or rejection is recorded.

Owner: Backend 1. Fill in after inspecting data/generator_raw/ and writing
data/field_mapping.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_raw(path: str | Path) -> Any:
    """Load the generator file as-is (CSV or JSON — TODO: match the real format)."""
    p = Path(path)
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    raise NotImplementedError(f"generator format {p.suffix} not handled yet")


def to_scenario(raw: Any, incident_id: str) -> tuple[dict[str, Any], list[str]]:
    """TODO(Backend 1): map raw generator rows to
    {"incident_id", "window_end", "records": [...]} and return (scenario, conversion_log)."""
    raise NotImplementedError("generator adapter not implemented yet")
