"""Connectivity Agent as a separate REST process — the real wire contract.

    uvicorn connectivity_service.app:app --port 8001

Validates every inbound message against the EXPORTED JSON Schema (schemas/*.json),
not the Python models, so a non-Python implementation could replace this service.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator

from connectivity_service.logic import AGENT_ID, handle_bundle
from netcoop.protocol.cards import CARDS
from netcoop.protocol.compat import UnsupportedVersion, parse_version
from netcoop.protocol.models import PROTOCOL_VERSION, Envelope, Observation

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
MESSAGE_V = Draft202012Validator(json.loads((SCHEMAS / "message-1.0.json").read_text(encoding="utf-8")))
OBS_V = Draft202012Validator(json.loads((SCHEMAS / "observation-1.0.json").read_text(encoding="utf-8")))

app = FastAPI(title="NetCoop Connectivity Agent")
_seen: set[str] = set()


@app.get("/card")
def card() -> dict[str, Any]:
    return CARDS[AGENT_ID].model_dump()


@app.post("/messages")
async def messages(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError as exc:
        return _error(None, "MALFORMED_JSON", str(exc), None)
    if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
        return _error(None, "MISSING_FIELD", "body must be a bundle with a 'messages' list", "messages")

    accepted: list[Envelope] = []
    for raw in body["messages"]:
        try:
            major, _ = parse_version(raw.get("protocol"))
            if major != 1:
                raise UnsupportedVersion(f"{raw.get('protocol')} not supported")
        except UnsupportedVersion as exc:
            return _error(raw, "SCHEMA_VERSION_UNSUPPORTED", str(exc), "protocol")
        errors = sorted(MESSAGE_V.iter_errors(raw), key=lambda e: list(e.path))
        if errors:
            e = errors[0]
            code = "MISSING_FIELD" if e.validator == "required" else "INVALID_VALUE"
            return _error(raw, code, e.message, ".".join(str(p) for p in e.path) or None)
        if raw["message_id"] in _seen:
            continue  # duplicate: ignored (orchestrator logs it)
        _seen.add(raw["message_id"])
        accepted.append(Envelope.model_validate(raw))

    observations = []
    for o in body.get("observations", []):
        errs = list(OBS_V.iter_errors(o))
        if errs:
            return _error(None, "INVALID_VALUE", f"observation: {errs[0].message}", "observations")
        observations.append(Observation.model_validate(o))

    out = handle_bundle(accepted, observations, body.get("topology", {}))
    return JSONResponse({"messages": [m.model_dump(mode="json") for m in out]})


def _error(raw: dict | None, code: str, detail: str, path: str | None) -> JSONResponse:
    raw = raw if isinstance(raw, dict) else {}
    incident = raw.get("incident_id") or "UNKNOWN"
    err = Envelope(
        protocol=PROTOCOL_VERSION,
        message_id=f"{incident}-CONN-ERR-{len(_seen) + 1:02d}",
        incident_id=incident,
        in_reply_to=raw.get("message_id"),
        sender=AGENT_ID,
        recipient=raw.get("sender") or "orchestrator",
        type="ERROR",
        timestamp=raw.get("timestamp") or datetime.now(timezone.utc),
        payload={"code": code, "detail": detail, "field_path": path,
                 "offending_message_id": raw.get("message_id")},
    )
    return JSONResponse({"messages": [err.model_dump(mode="json")]}, status_code=422)
