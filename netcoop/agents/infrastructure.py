"""Infrastructure Agent — device status, CPU/memory, queue drops, interface errors,
link flaps, Wi-Fi RSSI/retries.

Owner: Backend 2.
"""
from __future__ import annotations

from netcoop.agents.base import BaseAgent, IncidentContext
from netcoop.protocol.models import Envelope


class InfrastructureAgent(BaseAgent):
    agent_id = "infrastructure_agent"
    abbrev = "INF"

    def handle(self, msg: Envelope, ctx: IncidentContext) -> list[Envelope]:
        """On TASK(analyze_infrastructure): return FINDING envelopes.

        TODO(Backend 2):
        - counters are cumulative: use the per-interval deltas the normalizer computed;
          respect counter_reset flags
        - weak_wifi needs RSSI (grey zone -75..-67 = uncertain) AND retries AND healthy AP uplink
        - emit stance=contradicts when evidence argues against a likely rival, e.g.
          interface errors rising while utilization is normal -> contradicts link_congestion@<link>
        """
        return []
