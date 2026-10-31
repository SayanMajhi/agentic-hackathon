import json
from pathlib import Path

from fastapi.testclient import TestClient

from connectivity_service.app import app

EX = Path(__file__).resolve().parents[1] / "examples"
client = TestClient(app)


def load(name):
    return json.loads((EX / name).read_text(encoding="utf-8"))


def test_card():
    assert client.get("/card").json()["agent_id"] == "connectivity_agent"


def test_valid_task_gets_reply_to_it():
    task = load("task.json")
    task["message_id"] = "T-SVC-1"
    r = client.post("/messages", json={"messages": [task, load("finding.json")]})
    assert r.status_code == 200
    out = r.json()["messages"]
    assert out and out[0]["in_reply_to"] == "T-SVC-1"


def test_missing_field_is_typed_error():
    task = load("task.json")
    task["message_id"] = "T-SVC-2"
    del task["sender"]
    r = client.post("/messages", json={"messages": [task]})
    assert r.status_code == 422
    err = r.json()["messages"][0]
    assert err["type"] == "ERROR" and err["payload"]["code"] == "MISSING_FIELD"


def test_v2_is_unsupported():
    r = client.post("/messages", json={"messages": [load("message_v2_0.json")]})
    assert r.json()["messages"][0]["payload"]["code"] == "SCHEMA_VERSION_UNSUPPORTED"
