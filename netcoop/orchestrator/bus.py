"""Message bus: validates EVERY message before delivery. Invalid, duplicate or
unsupported messages become typed ERROR envelopes in the trace — never silent drops."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ValidationError

from netcoop.protocol.compat import UnsupportedVersion, upgrade
from netcoop.protocol.models import PROTOCOL_VERSION, Envelope, ErrorCode, MessageType
from netcoop.orchestrator.eventlog import EventLog


class MessageBus:
    def __init__(self, eventlog: EventLog, clock: datetime):
        self.log = eventlog
        self.clock = clock  # deterministic incident clock, not wall time
        self.seen: set[str] = set()
        self.conversions: list[str] = []
        self._err_seq = 0

    def deliver(self, raw: dict[str, Any], transport: str = "local") -> tuple[Envelope | None, Envelope | None]:
        """Return (accepted envelope, None) or (None, ERROR envelope)."""
        try:
            body, records = upgrade(raw)
        except UnsupportedVersion as exc:
            return None, self._reject(raw, ErrorCode.SCHEMA_VERSION_UNSUPPORTED, str(exc), "protocol", transport)

        try:
            env = Envelope.model_validate(body)
        except ValidationError as exc:
            first = exc.errors()[0]
            code = ErrorCode.MISSING_FIELD if first["type"] == "missing" else ErrorCode.INVALID_VALUE
            path = ".".join(str(p) for p in first["loc"])
            return None, self._reject(raw, code, first["msg"], path, transport)

        if env.message_id in self.seen:
            return None, self._reject(raw, ErrorCode.DUPLICATE_MESSAGE,
                                      f"duplicate message_id {env.message_id} ignored", "message_id", transport)
        self.seen.add(env.message_id)
        self.conversions.extend(f"{env.message_id}: {r}" for r in records)
        self.log.record(env.model_dump(mode="json"), valid=True, transport=transport)
        return env, None

    def _reject(self, raw: dict[str, Any], code: ErrorCode, detail: str, path: str | None,
                transport: str) -> Envelope:
        self.log.record(raw if isinstance(raw, dict) else {"raw": str(raw)}, valid=False,
                        error=f"{code.value}: {detail}", transport=transport)
        self._err_seq += 1
        incident = raw.get("incident_id") if isinstance(raw, dict) else None
        err = Envelope(
            protocol=PROTOCOL_VERSION,
            message_id=f"{incident or 'UNKNOWN'}-BUS-ERR-{self._err_seq:02d}",
            incident_id=incident or "UNKNOWN",
            in_reply_to=raw.get("message_id") if isinstance(raw, dict) else None,
            sender="orchestrator",
            recipient=(raw.get("sender") if isinstance(raw, dict) else None) or "unknown",
            type=MessageType.ERROR,
            timestamp=self.clock,
            payload={"code": code.value, "detail": detail, "field_path": path,
                     "offending_message_id": raw.get("message_id") if isinstance(raw, dict) else None},
        )
        self.log.record(err.model_dump(mode="json"), valid=True, transport="local")
        return err
