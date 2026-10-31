"""HTTP client for agents that run in a separate process (Connectivity)."""
from __future__ import annotations

from typing import Any

import httpx


class RemoteAgentError(RuntimeError):
    pass


def post_bundle(endpoint: str, bundle: dict[str, Any], timeout_s: float = 5.0, retries: int = 1) -> dict[str, Any]:
    """POST a bundle to <endpoint>/messages. Returns the raw JSON response (request and
    response bodies are both logged by the caller as wire proof)."""
    last: Exception | None = None
    for _ in range(retries + 1):
        try:
            resp = httpx.post(f"{endpoint}/messages", json=bundle, timeout=timeout_s)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
    raise RemoteAgentError(f"{endpoint} unreachable after {retries + 1} attempts: {last}")
