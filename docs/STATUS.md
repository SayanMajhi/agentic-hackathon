# NetCoop AI — Phase plan and status (PM tracker)

Statuses: NOT STARTED / IN PROGRESS / BLOCKED / READY FOR REVIEW / ACCEPTED.
A phase is ACCEPTED only when AI 3 (evaluator) says so against evidence. Members A–D are equal; the role labels in
`docs/PHASE1_TASKS.md` map as A = Lead, B = Backend 1, C = Backend 2, D = UI/demo.
Times are relative to T0 (hackathon start); 24-hour event. **Deadline: TBD — confirm and fill in.**

| # | Phase | Window | Deliverable | Status |
|---|---|---|---|---|
| 0 | Skeleton | done before T0 | runnable plumbing, draft protocol, CI | READY FOR REVIEW |
| 1 | Data contract (M1) | T0 → T+3h | frozen `netcoop/1.0`, raw generator data + field mapping, topology, REST proof, labels, dashboard mock | NOT STARTED |
| 2 | Specialist agents | T+3h → T+9h | normalizer, Performance, Infrastructure, Connectivity (REST, consumes peer findings), thresholds | NOT STARTED |
| 3 | Correlation + report | T+7h → T+13h | `heuristic-v1`, decision gates, QUERY rounds (≤2), 0.9 compat, report actions + Markdown | NOT STARTED |
| 4 | Robustness + evaluation | T+12h → T+17h | all 16 dev scenarios pass labels, held-out set, `netcoop eval` | NOT STARTED |
| 5 | Dashboard (optional, encouraged) | T+10h → T+18h | event feed, ranking, evidence, report view on real runs | NOT STARTED |
| 6 | Freeze + submission | T+18h → deadline | ARCHITECTURE/README final, demo video 3–5 min, rehearsal, repo tagged | NOT STARTED |

Feature freeze at **T+18h**: after that only fixes to mandatory requirements or demo failures.

## Phase acceptance criteria

**Phase 0 — Skeleton**
- `pytest -q` green on `main` (evidence 2026-10-31: 28 passed, 1 xfailed).
- `netcoop run scenarios/dev/sample_minimal.json --local` returns a schema-valid report (evidence: `insufficient_evidence`, 1 normalization log entry).
- `ARCHITECTURE.md` is the full document. Gap: `assets/` diagrams are missing.

**Phase 1 — Data contract** (detail per member in `docs/PHASE1_TASKS.md`)
1. `pytest tests/test_protocol.py tests/test_schema_drift.py` green; FINDING without `stance` fails naming the field; every example validates except v0.9 / v2.0.
2. `data/generator_raw/` holds untouched organizer output + `RETRIEVED.md`; `data/field_mapping.md` lists every raw key.
3. `signatures-1.0.yaml` loads with `version: "1.0"`; adapter runs on the raw file without crashing.
4. `scenarios/topology.json` has 10–14 devices, ≥2 APs, DNS/DHCP server, one shared upstream; IDs match generator IDs.
5. `docs/m1_curl_proof.md`: valid → RESPONSE, missing `sender` → typed ERROR, duplicate → logged + ignored, 3 SQLite rows.
6. `scenarios/labels.json` has no `TODO`; dashboard renders `examples/report_diagnosed.json` (screenshot); types generated from schemas.
7. `assets/*.png` diagrams added; `contract-1.0` git tag exists.

**Phase 2 — Specialist agents**
- Each agent emits schema-valid FINDINGs with `stance` and ≥1 real `evidence_id`; Infrastructure emits at least one `contradicts`.
- Connectivity runs as its own uvicorn process; its FINDING lists `consumed_message_ids`; `--control` run differs.
- Missing/stale values are flagged, never zero; counter reset flagged; unit conversion logged.

**Phase 3 — Correlation + report**
- Confidence computed exactly by the `heuristic-v1` formula; gates enforced; report contains every field in CLAUDE.md "Report fields".
- Unknown evidence ID → `UNKNOWN_EVIDENCE` ERROR, not a crash; correlation failure → `insufficient_evidence` + `correlation_failed`.
- 0.9 input upgraded with a visible conversion record; 2.x → `SCHEMA_VERSION_UNSUPPORTED`.

**Phase 4 — Robustness + evaluation**
- All 16 `scenarios/dev/*` match `labels.json` status/cause/affected IDs; `netcoop eval` prints confusion matrix and false-diagnosis rate.
- Runs are byte-identical for a fixed fixture and seed (excluding wall-clock).

**Phase 6 — Submission**
- Fresh clone → 3-command setup → `pytest` green → demo commands work (recorded).
- Demo video 3–5 min shows end-to-end diagnosis, inter-agent messages, final report, one failure case.
- README covers agent roles, interfaces, orchestration, correlation, error handling, workflow, limitations.

## Check-in log
- 2026-10-31 — Phase 0 verified by PM (tests + local run). Submitted to AI 3 for review. Phase 1 not started.
- 2026-10-31 — Clean base template rebuilt in `agentic_hacakathon_clean` from the skeleton commit + final ARCHITECTURE.md; committed locally, not pushed.
