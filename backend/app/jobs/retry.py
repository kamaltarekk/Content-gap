"""Deterministic retry policy (spec §6.7, §20.11). Pure and unit-testable.

Safe to auto-retry: connection failures before the request landed, short 429s, provider 5xx.
NOT safe to auto-retry: an ambiguous timeout where provider completion is unknown — retrying could
double-charge; it must be reconciled or retried manually. Validation/refusal never blind-retry.
"""

from __future__ import annotations

from dataclasses import dataclass


class TransientConnectionError(Exception):
    """Connection failed before the request was accepted — safe to retry."""


class RateLimitedError(Exception):
    """HTTP 429 with a short Retry-After — safe to retry once/queue later."""


class ProviderServerError(Exception):
    """Provider 5xx — retry per configured policy."""


class AmbiguousTimeoutError(Exception):
    """Timeout with unknown provider completion — do NOT auto-retry a paid request."""


class PermanentValidationError(Exception):
    """Schema/enum/evidence validation failure after repair — do not retry."""


class SafetyRefusalError(Exception):
    """Provider refusal/safety stop — mark distinctly, do not blind-retry."""


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    error_code: str
    reason: str


def classify(exc: BaseException, *, retry_count: int, max_retries: int) -> RetryDecision:
    can_retry_more = retry_count < max_retries
    if isinstance(exc, TransientConnectionError):
        return RetryDecision(can_retry_more, "connection_failed", "transient connection failure")
    if isinstance(exc, RateLimitedError):
        return RetryDecision(can_retry_more, "rate_limited", "429 rate limited")
    if isinstance(exc, ProviderServerError):
        return RetryDecision(can_retry_more, "provider_5xx", "provider server error")
    if isinstance(exc, AmbiguousTimeoutError):
        # Never auto-retry a possibly-completed paid request.
        return RetryDecision(False, "timeout_unknown_completion", "ambiguous timeout; reconcile manually")
    if isinstance(exc, PermanentValidationError):
        return RetryDecision(False, "validation_failed", "permanent validation failure")
    if isinstance(exc, SafetyRefusalError):
        return RetryDecision(False, "provider_refusal", "safety stop / refusal")
    # Unknown errors: do not blind-retry.
    return RetryDecision(False, "unknown_error", type(exc).__name__)
