"""Correlation Agent — ranks global signatures, weighs supports/contradicts, issues
QUERY when disputed/stale/close, abstains when necessary.

Owner: Lead.
"""
from __future__ import annotations

from netcoop.agents.base import BaseAgent, IncidentContext
from netcoop.protocol.models import Envelope, FindingPayload, MessageType, Status


def heuristic_v1(signal_fit: float, topology_fit: float, time_fit: float,
                 independent_source_fit: float, contradiction_strength: float,
                 coverage: float) -> float:
    """Confidence method `heuristic-v1` (ARCHITECTURE.md §4). All inputs in [0,1]."""
    raw = (0.40 * signal_fit + 0.25 * topology_fit + 0.20 * time_fit
           + 0.15 * independent_source_fit - 0.15 * contradiction_strength)
    return round(max(0.0, min(1.0, raw)) * coverage, 2)


class CorrelationAgent(BaseAgent):
    agent_id = "correlation_agent"
    abbrev = "CORR"

    def __init__(self) -> None:
        super().__init__()
        self.findings: list[Envelope] = []

    def handle(self, msg: Envelope, ctx: IncidentContext) -> list[Envelope]:
        if msg.type == MessageType.FINDING.value:
            self.findings.append(msg)
            return []
        if msg.type == MessageType.TASK.value:  # capability "correlate": decide now
            return [self.decide(msg, ctx)]
        return []

    def decide(self, task: Envelope, ctx: IncidentContext) -> Envelope:
        """TODO(Lead):
        - sort findings by stage, agent ID, evidence ID; dedupe evidence IDs
        - per hypothesis: signal/topology/time/independent-source fit, coverage, contradictions
        - apply decision gates (diagnosed/probable/healthy/insufficient_evidence)
        - if disputed/stale/thin or top-2 lead < 0.15: return a QUERY instead (max 2 rounds)
        """
        finding_ids = [FindingPayload.model_validate(f.payload).finding_id for f in self.findings]
        return self.make(ctx, "reporting_agent", MessageType.DECISION, {
            "decision_id": f"{ctx.incident_id}-DEC-01",
            "status": Status.insufficient_evidence.value,
            "ranking": [],
            "limitations": [f"correlation not implemented; {len(finding_ids)} findings received"],
        }, in_reply_to=task.message_id)
