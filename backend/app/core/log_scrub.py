"""Log / error-report scrubbing (spec §25.4, §31.5).

Structured logs and error reports may contain identifiers, sizes, states, and error codes — but
never complete evidence text, authorization headers, provider keys, or raw PII. ``scrub`` enforces
that before anything is logged or sent to a Sentry-compatible reporter.
"""

from __future__ import annotations

from typing import Any

from app.core.pii import redact

# Keys whose values must never be emitted verbatim.
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "api_key",
    "anthropic_api_key",
    "session_secret",
    "password",
    "token",
    "secret",
    "quoted_text",
    "original_text",
    "normalized_text",
    "verbatim_phrase",
    "evidence",
    "text",
    "raw",
}
_REDACTED = "[REDACTED]"
_MAX_STR = 500


def _scrub_value(key: str, value: Any) -> Any:
    if key.lower() in _SENSITIVE_KEYS:
        return _REDACTED
    if isinstance(value, dict):
        return {k: _scrub_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(key, v) for v in value]
    if isinstance(value, str):
        # Redact any PII that slipped into a non-sensitive field, and cap length.
        redacted, _counts = redact(value)
        return redacted[:_MAX_STR]
    return value


def scrub(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of an event dict safe for logs / error reporting."""
    return {k: _scrub_value(k, v) for k, v in event.items()}


class ErrorReporter:
    """Sentry-compatible reporter shim. In local/test mode it records scrubbed events in memory so
    tests can assert no raw PII/evidence leaves the process. A production build swaps in a real
    Sentry client that receives the SAME scrubbed payloads."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def capture(self, message: str, **context: Any) -> dict[str, Any]:
        event = scrub({"message": message, **context})
        self.events.append(event)
        return event


error_reporter = ErrorReporter()
