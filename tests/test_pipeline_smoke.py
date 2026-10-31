"""End-to-end skeleton: must always produce a schema-valid report, whatever is stubbed."""
import json
from pathlib import Path

from netcoop.orchestrator.run import load_signatures, run_incident
from netcoop.protocol.models import Report

ROOT = Path(__file__).resolve().parents[1]
TOPO = json.loads((ROOT / "scenarios" / "topology.json").read_text(encoding="utf-8"))


def test_sample_runs_end_to_end_locally():
    raw = json.loads((ROOT / "scenarios" / "dev" / "sample_minimal.json").read_text(encoding="utf-8"))
    res = run_incident(raw, TOPO, load_signatures(), connectivity="local")
    Report.model_validate(res.report.model_dump(mode="json"))
    assert "rtt_sec 0.28 -> latency_ms 280" in res.report.normalization_log
    assert any(r["sender"] == "connectivity_agent" for r in res.eventlog.rows())


def test_missing_records_is_invalid_input():
    res = run_incident({"incident_id": "INC-X", "window_end": "2026-10-31T10:30:00Z"}, TOPO,
                       load_signatures(), connectivity="local")
    assert res.report.status == "invalid_input" and res.report.validation_errors


def test_unreachable_connectivity_still_reports():
    raw = json.loads((ROOT / "scenarios" / "dev" / "sample_minimal.json").read_text(encoding="utf-8"))
    res = run_incident(raw, TOPO, load_signatures(), connectivity="remote", endpoint="http://127.0.0.1:9")
    assert any("connectivity_agent unavailable" in l for l in res.report.limitations)


def test_deterministic():
    raw = json.loads((ROOT / "scenarios" / "dev" / "sample_minimal.json").read_text(encoding="utf-8"))
    a = run_incident(raw, TOPO, load_signatures(), connectivity="local").report.model_dump(mode="json")
    b = run_incident(raw, TOPO, load_signatures(), connectivity="local").report.model_dump(mode="json")
    assert a == b
