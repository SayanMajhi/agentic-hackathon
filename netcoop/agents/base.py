"""Shared agent plumbing. Agents import only netcoop.protocol and this module —
never each other."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from netcoop.protocol.models import PROTOCOL_VERSION, Envelope, MessageType, Observation


@dataclass
class IncidentContext:
    """Read-only view of the incident that every agent receives."""

    incident_id: str
    clock: datetime                      # deterministic incident time (window end)
    observations: list[Observation]
    topology: dict[str, Any]
    signatures: dict[str, Any]           # parsed config/signatures-1.0.yaml
    normalization_log: list[str] = field(default_factory=list)

    def evidence(self, evidence_id: str) -> Observation | None:
        return next((o for o in self.observations if o.evidence_id == evidence_id), None)

    def by_metric(self, metric: str) -> list[Observation]:
        return [o for o in self.observations if o.metric == metric]


class BaseAgent:
    agent_id: str = "base"
    abbrev: str = "BASE"   # used in deterministic message IDs, e.g. INC-0001-PERF-01

    def __init__(self) -> None:
        self._seq = 0

    def handle(self, msg: Envelope, ctx: IncidentContext) -> list[Envelope]:
        raise NotImplementedError

    def make(self, ctx: IncidentContext, recipient: str, type_: MessageType,
             payload: dict[str, Any], in_reply_to: str | None) -> Envelope:
        self._seq += 1
        return Envelope(
            protocol=PROTOCOL_VERSION,
            message_id=f"{ctx.incident_id}-{self.abbrev}-{self._seq:02d}",
            incident_id=ctx.incident_id,
            in_reply_to=in_reply_to,
            sender=self.agent_id,
            recipient=recipient,
            type=type_,
            timestamp=ctx.clock,
            payload=payload,
        )
