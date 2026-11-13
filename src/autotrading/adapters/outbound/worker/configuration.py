from dataclasses import dataclass, field

from autotrading.adapters.outbound.worker.account_state import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _WorkerSettings:
    """How the API reaches the worker: its internal address and the token generated on the machine (ADR 0021)."""

    url: str
    token: str = field(repr=False)
    timeout_seconds: float = TIMEOUT_SECONDS
