"""Capability registry built from agent cards."""
from __future__ import annotations

from netcoop.protocol.cards import CARDS, AgentCard

CANONICAL_METRICS = [
    "latency_ms", "jitter_ms", "packet_loss_pct", "throughput_mbps", "capacity_mbps",
    "link_utilization_pct", "cpu_pct", "memory_pct", "queue_drops", "interface_errors",
    "link_flap_count", "interface_oper_status", "rssi_dbm", "retry_rate_pct",
    "dns_success", "dhcp_success", "reachability",
]


class Registry:
    def __init__(self, cards: dict[str, AgentCard] | None = None):
        self.cards = dict(cards or CARDS)

    def by_capability(self, capability: str) -> AgentCard:
        for card in self.cards.values():
            if capability in card.capabilities:
                return card
        raise KeyError(f"no agent advertises capability '{capability}'")

    def supports(self, agent_id: str, protocol: str) -> bool:
        return protocol in self.cards[agent_id].protocol_versions

    def uncovered_metrics(self, present: set[str]) -> list[str]:
        """Metrics present in the data that no agent card owns — reported as a limitation."""
        owned = {m for c in self.cards.values() for m in c.owned_metrics}
        return sorted(present - owned)
