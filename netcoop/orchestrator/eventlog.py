"""SQLite event log: every delivered or rejected message lands here (core, not optional)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id  TEXT,
    message_id   TEXT,
    protocol     TEXT,
    sender       TEXT,
    recipient    TEXT,
    type         TEXT,
    in_reply_to  TEXT,
    valid        INTEGER NOT NULL,
    error        TEXT,
    transport    TEXT,
    body_json    TEXT NOT NULL,
    received_at  TEXT NOT NULL
)
"""


class EventLog:
    def __init__(self, path: str | Path = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.execute(SCHEMA)

    def record(self, body: dict[str, Any], valid: bool, error: str | None = None,
               transport: str = "local") -> None:
        self.conn.execute(
            "INSERT INTO events (incident_id, message_id, protocol, sender, recipient, type,"
            " in_reply_to, valid, error, transport, body_json, received_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                body.get("incident_id"), body.get("message_id"), body.get("protocol"),
                body.get("sender"), body.get("recipient"), body.get("type"),
                body.get("in_reply_to"), int(valid), error, transport,
                json.dumps(body, sort_keys=True, default=str),
                # wall-clock: operational only, excluded from reproducibility snapshots
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def rows(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM events ORDER BY seq")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def export_jsonl(self, path: str | Path, include_wallclock: bool = False) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for row in self.rows():
                if not include_wallclock:
                    row.pop("received_at")
                row["body"] = json.loads(row.pop("body_json"))
                fh.write(json.dumps(row, sort_keys=True) + "\n")
