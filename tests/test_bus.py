import json
from datetime import datetime, timezone
from pathlib import Path

from netcoop.orchestrator.bus import MessageBus
from netcoop.orchestrator.eventlog import EventLog

EX = Path(__file__).resolve().parents[1] / "examples"
CLOCK = datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc)


def load(name):
    return json.loads((EX / name).read_text(encoding="utf-8"))


def test_valid_then_duplicate_then_invalid_all_logged():
    log = EventLog()
    bus = MessageBus(log, CLOCK)
    env, err = bus.deliver(load("finding.json"))
    assert env and err is None

    env, err = bus.deliver(load("finding.json"))
    assert env is None and err.payload["code"] == "DUPLICATE_MESSAGE"

    bad = load("finding.json")
    bad["message_id"] = "INC-0001-INF-99"
    del bad["sender"]
    env, err = bus.deliver(bad)
    assert env is None and err.payload["code"] == "MISSING_FIELD" and err.payload["field_path"] == "sender"

    rows = log.rows()
    assert [r["valid"] for r in rows] == [1, 0, 1, 0, 1]  # rejects are followed by their ERROR envelope


def test_v2_returns_unsupported_error():
    bus = MessageBus(EventLog(), CLOCK)
    env, err = bus.deliver(load("message_v2_0.json"))
    assert env is None and err.payload["code"] == "SCHEMA_VERSION_UNSUPPORTED"
