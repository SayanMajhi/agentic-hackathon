# Phase 1 (Milestone M1) — Data contract ready

**Window:** T0 → T+3h. **Repo:** https://github.com/SayanMajhi/agentic-hackathon
**Rule:** no agent logic, no UI features. Only: raw data, field mapping, frozen contract, agent cards, a REST service that validates.
Every member: paste `CLAUDE.md` into your AI first (Claude Code reads it automatically), then your section below as "MY TASK RIGHT NOW".

## Step 0 — skeleton (DONE in the base commit)
Already in place, runs end to end, `pytest -q` → 28 passed + 1 expected xfail:
- Layout, `pyproject.toml` (`netcoop` CLI), CI workflow, `.gitignore`.
- **Draft** protocol models + generated schemas + PROTOCOL.md field table, agent cards, compat (1.x/2.x done; 0.9 TODO), examples for every message type.
- Bus (validation, typed ERRORs, duplicate drop), SQLite event log, registry, REST client, pipeline with correlation fallback.
- Connectivity FastAPI service validating against exported JSON Schema; wire request/response logged in traces.
- Agent stubs with `TODO(<owner>)` docstrings; sample topology + sample scenario (replace both); signatures YAML with `null` thresholds.
- Dashboard: Vite React-TS scaffold + `npm run gen:types`.

Remaining Step 0 for Lead: `ARCHITECTURE.md` is in place; add its two diagrams `assets/system-architecture.png` and `assets/diagnostic-workflow.png`.
Everyone: `git pull`, `pip install -e ".[dev]"`, `pytest -q` green, then branch `m1/<role>-<topic>`; PR + 1 review, merge within 2h.
**Your sections below are now "fill the TODOs in these files", not "create these files".**

## Lead — protocol
- [ ] `netcoop/protocol/models.py`: `Envelope` (`protocol, message_id, incident_id, in_reply_to, sender, recipient, type, timestamp, payload, extra`); payload models for `TASK, FINDING, QUERY, RESPONSE, DECISION, ERROR`; `Observation`; `Report`; enums `MessageType`, `Stance`, `Status` (6 values), `ErrorCode` (incl. `SCHEMA_VERSION_UNSUPPORTED`, `MISSING_FIELD`, `INVALID_VALUE`, `DUPLICATE_MESSAGE`, `UNKNOWN_EVIDENCE`).
- [ ] FINDING payload: `finding_id, hypothesis (cause@id), stance, target_hypothesis, evidence_ids[] (min 1), reason, consumed_message_ids[]`.
- [ ] Report validators: diagnosed/probable need a cause; others `suspected_root_cause=null`; invalid_input/failed need `confidence=null`.
- [ ] `netcoop/protocol/export.py` → `schemas/message-1.0.json`, `finding-1.0.json`, `report-1.0.json` + field table in `PROTOCOL.md`.
- [ ] `tests/test_schema_drift.py`: regenerate to temp dir, fail on diff with checked-in schemas.
- [ ] `netcoop/protocol/cards.py`: 5 agent cards (`agent_id, endpoint, protocol_versions, owned_metrics, hypotheses`).
- [ ] `examples/`: one valid message per type, `finding_v0_9.json`, `message_v2_0.json`, `report_diagnosed.json`, `report_insufficient.json`, `report_invalid_input.json`.
- [ ] After Backend 1's mapping lands: adjust metric names, then tag `contract-1.0`.

**Accept:** `pytest tests/test_protocol.py tests/test_schema_drift.py` green; FINDING without `stance` → validation error naming the field; all example files validate (except v0.9/v2.0 which must fail 1.0 validation).

## Backend 1 — generator + signatures
- [ ] **First, before anything:** run the organizer Colab generator unmodified; save output to `data/generator_raw/` (all scenario types it offers). `data/generator_raw/RETRIEVED.md`: date, notebook URL, revision/copy, parameters, seeds, whether labels exist.
- [ ] `data/field_mapping.md`: table — raw key | example value | unit | interval | nulls behaviour | canonical metric | conversion | mapped/rejected+reason. Also: topology representation, timestamp format/timezone, counter vs rate.
- [ ] **Hand mapping to Lead by T+1.5h** (post in team chat). If generator inaccessible or unlabeled, say so by then.
- [ ] `netcoop/config/signatures-1.0.yaml`: `version`, thresholds per metric (normal/warn/critical + rationale), window (5 min, ≥3 consecutive), RSSI grey zone (-75..-67), the 4 signatures (required checks, corroborating checks, contradicting checks), healthy-coverage rule, decision gates.
- [ ] `netcoop/normalizer/adapter_generator.py` stub: load raw file → list of dicts with `original_field/original_value` preserved (conversion can be partial).

**Accept:** every raw key appears in mapping; YAML loads with `version: "1.0"`; adapter runs on the untouched raw file without crashing.

## Backend 2 — topology + REST + bus
- [ ] `scenarios/topology.json`: nodes (`id, type, zone`), links (`link_id, a, b, capacity_mbps`); ~10–14 devices incl. core router, hostel + dept distribution switches, access switches, ≥2 APs, DNS/DHCP server; **one shared upstream** for blast-radius. IDs must match generator device IDs if the generator has them (coordinate with Backend 1).
- [ ] `connectivity_service/app.py` (FastAPI): `GET /card`, `POST /messages` validating body with `jsonschema` against `schemas/message-1.0.json`; valid → stub RESPONSE envelope (correct `in_reply_to`); invalid → ERROR envelope with field path + code. Runs on its own: `uvicorn connectivity_service.app:app --port 8001`.
- [ ] `netcoop/orchestrator/bus.py`: `deliver(msg)` validates, rejects duplicate `message_id` (logged), returns ERROR envelope on failure.
- [ ] `netcoop/orchestrator/eventlog.py`: SQLite table (message_id, incident_id, sender, recipient, type, protocol, in_reply_to, valid, error, body_json, received_at).
- [ ] Stub `netcoop/agents/infrastructure.py` with `handle(envelope) -> list[Envelope]`.

**Accept:** curl valid → 200 RESPONSE; curl missing `sender` → typed ERROR; duplicate ID → logged + ignored; all three rows visible in SQLite. Save curl outputs to `docs/m1_curl_proof.md`.

## UI/demo — dashboard scaffold + labels
- [ ] `dashboard/` React + Vite + TS; generate types from `schemas/*.json` (`json-schema-to-typescript`) — no hand-typed field names.
- [ ] Mock views reading `examples/`: event feed (sender → recipient, type, validity), competing causes, evidence ID list, status badge (all 6), raw JSON panel.
- [ ] `scenarios/labels.json` for the §7 dev list: normal, false report, congestion, weak Wi-Fi, interface fault, DNS, DHCP, ambiguous congestion+errors, missing/stale, unit mismatch, counter reset, schema 0.9, unsupported 2.x, missing message field, duplicate message, correlation timeout → expected `status`, `cause`, `affected_ids`.
- [ ] `docs/DEMO_SCRIPT.md` draft (architecture §7 demo sequence, timed to 4 min); README skeleton (3-command setup, test/eval commands, limitations section).

**Accept:** `npm run dev` renders `examples/report_diagnosed.json`; labels cover all 16 classes; types regenerate from schemas.

## M1 exit gate — bring to review
1. Link to `main` after merges (or paste): `models.py`, generated `schemas/`, `PROTOCOL.md`.
2. `data/generator_raw/` + `RETRIEVED.md` + `field_mapping.md`.
3. `docs/m1_curl_proof.md`.
4. `labels.json` + dashboard screenshot.
5. `pytest` output.
