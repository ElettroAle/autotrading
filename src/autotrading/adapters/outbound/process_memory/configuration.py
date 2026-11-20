from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _ProcessMemorySettings:
    """How long the API keeps a reading of an account for the dashboard: the owner chose 10 seconds (Bug 635)."""

    account_activity_validity_seconds: float = 10.0
