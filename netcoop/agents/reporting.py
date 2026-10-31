"""Reporting Agent — validates IDs and serializes report-1.0 JSON + Markdown, using
only cited findings.

Owner: Lead + Backend 2.
"""
from __future__ import annotations

from netcoop.agents.base import IncidentContext
from netcoop.protocol.models import (
    DecisionPayload, Envelope, EvidenceItem, FindingPayload, Report, Status,
)

SIGNATURE_VERSION_KEY = "version"


def build_report(decision: Envelope, findings: list[Envelope], ctx: IncidentContext,
                 extra_limitations: list[str] | None = None) -> Report:
    d = DecisionPayload.model_validate(decision.payload)
    fps = [FindingPayload.model_validate(f.payload) for f in findings]
    top = d.ranking[0] if d.ranking else None
    named = d.status in (Status.diagnosed.value, Status.probable.value)

    cited = {eid for fp in fps for eid in fp.evidence_ids}
    evidence = []
    for eid in sorted(cited):
        obs = ctx.evidence(eid)
        if obs is None:
            raise ValueError(f"finding cites unknown evidence {eid}")  # TODO: UNKNOWN_EVIDENCE ERROR
        evidence.append(EvidenceItem(evidence_id=eid, metric=obs.metric, value=obs.value,
                                     unit=obs.unit, source_id=obs.source_id))

    # TODO(Lead/Backend 2): affected IDs from topology, recommended actions per cause,
    # alternative causes from ranking[1:], Markdown rendering.
    return Report(
        incident_id=ctx.incident_id,
        status=d.status,
        suspected_root_cause=top.hypothesis if (named and top) else None,
        confidence=top.confidence if top else (None if d.status in ("invalid_input", "failed") else 0.0),
        signature_version=str(ctx.signatures.get(SIGNATURE_VERSION_KEY, "unknown")),
        supporting_evidence=evidence,
        agent_findings=sorted(fp.finding_id for fp in fps),
        alternative_causes=[r.hypothesis for r in d.ranking[1:]],
        evidence_sources=sorted({f.sender for f in findings}),
        limitations=d.limitations + (extra_limitations or []),
        normalization_log=ctx.normalization_log,
        agent_trace_id=f"{ctx.incident_id}-TRACE",
    )
