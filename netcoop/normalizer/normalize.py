"""Normalizer service (NOT an agent): raw records -> canonical Observations with
provenance and quality flags.

Owner: Backend 1.

Input scenario shape (until the generator adapter defines the real one):
    {"incident_id": "INC-0001", "window_end": "<ISO8601>",
     "records": [{"source_id": "...", "observed_at": "...", "device_id" | "link_id": "...",
                  "<metric or alias>": value, ...}]}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from netcoop.protocol.models import Observation, QualityFlag

ID_KEYS = {"source_id", "observed_at", "device_id", "link_id", "timestamp"}

# TODO(Backend 1): replace with the aliases/units observed in data/field_mapping.md.
ALIASES: dict[str, tuple[str, str]] = {
    # raw_key: (canonical_metric, unit)
    "latency_ms": ("latency_ms", "ms"),
    "jitter_ms": ("jitter_ms", "ms"),
    "packet_loss_pct": ("packet_loss_pct", "percent"),
    "throughput_mbps": ("throughput_mbps", "Mbps"),
    "capacity_mbps": ("capacity_mbps", "Mbps"),
    "link_utilization_pct": ("link_utilization_pct", "percent"),
    "cpu_pct": ("cpu_pct", "percent"),
    "memory_pct": ("memory_pct", "percent"),
    "queue_drops": ("queue_drops", "packets"),
    "interface_errors": ("interface_errors", "count"),
    "link_flap_count": ("link_flap_count", "count"),
    "interface_oper_status": ("interface_oper_status", "enum"),
    "rssi_dbm": ("rssi_dbm", "dBm"),
    "retry_rate_pct": ("retry_rate_pct", "percent"),
    "retries": ("retry_rate_pct", "percent"),
    "retransmissions": ("retry_rate_pct", "percent"),
    "dns_success": ("dns_success", "bool"),
    "dhcp_success": ("dhcp_success", "bool"),
    "reachability": ("reachability", "bool"),
}
# raw_key: (canonical_metric, unit, factor) — e.g. seconds -> ms
CONVERSIONS: dict[str, tuple[str, str, float]] = {
    "rtt_sec": ("latency_ms", "ms", 1000.0),
}


@dataclass
class NormalizationResult:
    incident_id: str
    clock: datetime
    observations: list[Observation] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)   # non-empty => invalid_input


def normalize(raw: Any, topology: dict[str, Any]) -> NormalizationResult:
    """TODO(Backend 1): 5-min windows, median/p95, counter deltas + reset flags,
    stale detection vs window_end, utilization derivation and cross-check,
    topology ID validation. Missing/malformed values stay null with a flag — never 0."""
    if not isinstance(raw, dict):
        return NormalizationResult("UNKNOWN", datetime(1970, 1, 1), errors=["scenario root must be an object"])
    errors: list[str] = []
    for key in ("incident_id", "window_end", "records"):
        if key not in raw:
            errors.append(f"missing required field '{key}'")
    if errors:
        return NormalizationResult(str(raw.get("incident_id", "UNKNOWN")), datetime(1970, 1, 1), errors=errors)

    res = NormalizationResult(raw["incident_id"], datetime.fromisoformat(raw["window_end"].replace("Z", "+00:00")))
    known_ids = {n["id"] for n in topology.get("nodes", [])} | {l["link_id"] for l in topology.get("links", [])}
    seq = 0
    for i, rec in enumerate(raw["records"]):
        target = rec.get("device_id") or rec.get("link_id")
        if known_ids and target not in known_ids:
            res.errors.append(f"records[{i}]: unknown device/link id {target!r}")
            continue
        for key in sorted(k for k in rec if k not in ID_KEYS):
            value, steps, flags = rec[key], [], []
            if key in CONVERSIONS:
                metric, unit, factor = CONVERSIONS[key]
                if isinstance(value, (int, float)):
                    steps.append(f"{key} {value} -> {metric} {value * factor:g}")
                    value = value * factor
                    flags.append(QualityFlag.unit_converted)
            elif key in ALIASES:
                metric, unit = ALIASES[key]
                if key != metric:
                    steps.append(f"alias {key} -> {metric}")
                    flags.append(QualityFlag.alias_mapped)
            else:
                res.log.append(f"records[{i}]: unmapped field '{key}' ignored")
                continue
            if value is None:
                flags.append(QualityFlag.missing)
            seq += 1
            res.observations.append(Observation(
                evidence_id=f"EV-{seq:03d}",
                source_id=rec.get("source_id", "unknown"),
                observed_at=rec.get("observed_at") or rec.get("timestamp") or res.clock,
                device_id=rec.get("device_id"),
                link_id=rec.get("link_id"),
                metric=metric, value=value, unit=unit,
                original_field=key, original_value=rec[key],
                normalization_steps=steps,
                quality_flags=flags or [QualityFlag.ok],
            ))
            res.log.extend(steps)
    return res
