"""Orchestrator pipeline (ARCHITECTURE.md §4):

normalize -> TASK perf + infra -> forward their FINDINGs to Connectivity (REST) ->
Correlation (QUERY rounds, TODO) -> DECISION -> Reporting -> report + trace.

Owner: Backend 2 (orchestration, retries, fallback); Lead (correlation loop).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from netcoop.agents.base import BaseAgent, IncidentContext
from netcoop.agents.correlation import CorrelationAgent
from netcoop.agents.infrastructure import InfrastructureAgent
from netcoop.agents.performance import PerformanceAgent
from netcoop.agents.reporting import build_report
from netcoop.normalizer.normalize import normalize
from netcoop.orchestrator.bus import MessageBus
from netcoop.orchestrator.eventlog import EventLog
from netcoop.orchestrator.registry import Registry
from netcoop.orchestrator.remote import RemoteAgentError, post_bundle
from netcoop.protocol.models import Envelope, MessageType, Report, Status

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SIGNATURES = REPO_ROOT / "netcoop" / "config" / "signatures-1.0.yaml"


def load_signatures(path: Path = DEFAULT_SIGNATURES) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class _Orchestrator(BaseAgent):
    agent_id = "orchestrator"
    abbrev = "ORCH"


@dataclass
class RunResult:
    report: Report
    eventlog: EventLog


def run_incident(raw: Any, topology: dict[str, Any], signatures: dict[str, Any],
                 connectivity: str = "remote", endpoint: str | None = None,
                 drop_peer_findings: bool = False) -> RunResult:
    """connectivity: 'remote' (REST process, the real demo) or 'local' (tests only).
    drop_peer_findings: control run — Connectivity gets no peer findings."""
    log = EventLog()
    norm = normalize(raw, topology)
    if norm.errors:
        return RunResult(_terminal(norm.incident_id, Status.invalid_input, signatures,
                                   validation_errors=norm.errors, log=norm.log), log)

    ctx = IncidentContext(norm.incident_id, norm.clock, norm.observations, topology, signatures, norm.log)
    bus = MessageBus(log, ctx.clock)
    registry = Registry()
    orch = _Orchestrator()
    limitations: list[str] = []
    present = {o.metric for o in ctx.observations}
    if uncovered := registry.uncovered_metrics(present):
        limitations.append(f"no agent owns metrics: {uncovered}")

    def send(msg: Envelope, transport: str = "local") -> Envelope | None:
        env, err = bus.deliver(msg.model_dump(mode="json"), transport)
        return env

    # 1) parallel first pass (sequential here; order is deterministic)
    findings: list[Envelope] = []
    for agent, capability in ((PerformanceAgent(), "analyze_performance"),
                              (InfrastructureAgent(), "analyze_infrastructure")):
        task = send(orch.make(ctx, agent.agent_id, MessageType.TASK, {
            "task_id": f"{ctx.incident_id}-T-{agent.abbrev}", "capability": capability,
            "evidence_ids": [o.evidence_id for o in ctx.observations]}, in_reply_to=None))
        for out in agent.handle(task, ctx):
            if (env := send(out)) and env.type == MessageType.FINDING.value:
                findings.append(env)

    # 2) peer interpretation by Connectivity (separate process)
    peers = [] if drop_peer_findings else list(findings)
    conn_task = send(orch.make(ctx, "connectivity_agent", MessageType.TASK, {
        "task_id": f"{ctx.incident_id}-T-CONN", "capability": "interpret_peer_findings",
        "peer_message_ids": [p.message_id for p in peers]}, in_reply_to=None))
    bundle = {"messages": [m.model_dump(mode="json") for m in [conn_task, *peers]],
              "observations": [o.model_dump(mode="json") for o in ctx.observations],
              "topology": topology}
    try:
        if connectivity == "remote":
            ep = endpoint or registry.cards["connectivity_agent"].endpoint
            log.record({"wire": "request", "endpoint": f"{ep}/messages", "body": bundle}, True, transport="http")
            resp = post_bundle(ep, bundle)
            log.record({"wire": "response", "endpoint": f"{ep}/messages", "body": resp}, True, transport="http")
        else:
            from connectivity_service.logic import handle_bundle
            resp = {"messages": [m.model_dump(mode="json") for m in handle_bundle(
                [conn_task, *peers], ctx.observations, topology)]}
        for raw_msg in resp.get("messages", []):
            env, _ = bus.deliver(raw_msg, transport="http" if connectivity == "remote" else "local")
            if env and env.type == MessageType.FINDING.value:
                findings.append(env)
    except RemoteAgentError as exc:
        limitations.append(f"connectivity_agent unavailable: {exc}")

    # 3) correlation, one retry, then fallback
    corr = CorrelationAgent()
    for f in findings:
        corr.handle(f, ctx)
    decision = None
    for attempt in range(2):
        try:
            task = send(orch.make(ctx, corr.agent_id, MessageType.TASK, {
                "task_id": f"{ctx.incident_id}-T-CORR-{attempt + 1}", "capability": "correlate"},
                in_reply_to=None))
            outs = corr.handle(task, ctx)  # TODO(Lead): QUERY rounds (max 2) handled here
            decision = next((send(o) for o in outs if o.type == MessageType.DECISION.value), None)
            if decision:
                break
        except Exception as exc:  # noqa: BLE001 — any agent failure must still yield a report
            limitations.append(f"correlation attempt {attempt + 1} failed: {exc}")
    if decision is None:
        decision = send(orch.make(ctx, "reporting_agent", MessageType.DECISION, {
            "decision_id": f"{ctx.incident_id}-DEC-FALLBACK",
            "status": Status.insufficient_evidence.value if findings else Status.failed.value,
            "ranking": [], "limitations": ["correlation_failed"]}, in_reply_to=None))

    if bus.conversions:
        ctx.normalization_log.extend(bus.conversions)
    report = build_report(decision, findings, ctx, limitations)
    return RunResult(report, log)


def _terminal(incident_id: str, status: Status, signatures: dict[str, Any],
              validation_errors: list[str] | None = None, log: list[str] | None = None) -> Report:
    return Report(incident_id=incident_id, status=status, suspected_root_cause=None, confidence=None,
                  signature_version=str(signatures.get("version", "unknown")),
                  validation_errors=validation_errors or [], normalization_log=log or [],
                  agent_trace_id=f"{incident_id}-TRACE")


def write_outputs(result: RunResult, out_dir: Path, trace_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rp = out_dir / f"{result.report.incident_id}.json"
    rp.write_text(json.dumps(result.report.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    tp = trace_dir / f"{result.report.incident_id}.jsonl"
    result.eventlog.export_jsonl(tp)
    return rp, tp
