"""Connectivity Agent logic — topology, blast radius, common upstream dependency,
DNS/DHCP, reachability. Runs inside the separate REST process (app.py); importable
in-process only for tests.

Owner: Backend 2.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from netcoop.protocol.models import (
    PROTOCOL_VERSION, Envelope, FindingPayload, MessageType, Observation,
)

AGENT_ID = "connectivity_agent"
ABBREV = "CONN"


def handle_bundle(messages: list[Envelope], observations: list[Observation],
                  topology: dict[str, Any]) -> list[Envelope]:
    """Expects one TASK plus the peer FINDINGs it lists in payload.peer_message_ids.

    TODO(Backend 2):
    - build the topology graph; for each peer finding, map its hypothesis target to
      downstream devices (blast radius) and look for a shared upstream dependency
    - DNS/DHCP: service failure vs general path failure
    - every FINDING you emit must list the peer messages it used in consumed_message_ids
    - CONTROL RUN: same input without the peer findings must give a different conclusion
    """
    task = next((m for m in messages if m.type == MessageType.TASK.value), None)
    if task is None:
        return []
    peers = [m for m in messages if m.type == MessageType.FINDING.value]
    peer_hyps = [FindingPayload.model_validate(p.payload).hypothesis for p in peers]
    # Placeholder: answers with a RESPONSE describing what it received (wire proof).
    return [_make(task, 1, MessageType.RESPONSE, {
        "query_id": None,
        "evidence_ids": [],
        "answer": f"received {len(peers)} peer findings {peer_hyps}; "
                  f"{len(observations)} observations; {len(topology.get('nodes', []))} nodes "
                  "(connectivity logic not implemented)",
    })]


def _make(task: Envelope, seq: int, type_: MessageType, payload: dict[str, Any]) -> Envelope:
    return Envelope(
        protocol=PROTOCOL_VERSION,
        message_id=f"{task.incident_id}-{ABBREV}-{seq:02d}",
        incident_id=task.incident_id,
        in_reply_to=task.message_id,
        sender=AGENT_ID,
        recipient="correlation_agent",
        type=type_,
        timestamp=task.timestamp if isinstance(task.timestamp, datetime) else task.timestamp,
        payload=payload,
    )
