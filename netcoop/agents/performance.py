"""Performance Agent — latency, jitter, loss, throughput vs capacity, utilization, congestion.

Owner: Backend 1.
"""
from __future__ import annotations

from netcoop.agents.base import BaseAgent, IncidentContext
from netcoop.protocol.models import Envelope


class PerformanceAgent(BaseAgent):
    agent_id = "performance_agent"
    abbrev = "PERF"

    def handle(self, msg: Envelope, ctx: IncidentContext) -> list[Envelope]:
        """On TASK(analyze_performance): return FINDING envelopes to correlation_agent.

        TODO(Backend 1):
        - median/p95 latency & loss per window, sustained utilization (>=3 consecutive samples)
        - derive utilization from throughput/capacity, cross-check when both present
        - thresholds ONLY from ctx.signatures (config/signatures-1.0.yaml)
        - emit stance=supports for link_congestion@<link> or healthy@<scope>, citing evidence IDs
        - missing/stale evidence lowers score; never treat missing as 0
        """
        return []
