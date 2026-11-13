from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from autotrading.domain.verification.errors import VerificationInProgressError
from autotrading.domain.verification.verification_run import VerificationRun

type RunningVerifications = set[tuple[UUID, str]]


class InMemoryVerificationRunRepositoryAdapter:
    """The runs of the procedure of one tenant, as the database records them, and the ones in progress by account and
    asset, as the database locks them for every tenant."""

    def __init__(self, in_progress: RunningVerifications | None = None) -> None:
        self.runs: list[VerificationRun] = []
        self.in_progress: RunningVerifications = set() if in_progress is None else in_progress

    def add(self, run: VerificationRun) -> None:
        self.runs.append(run)

    @contextmanager
    def running(self, account_id: UUID, coin: str) -> Iterator[None]:
        key = (account_id, coin)
        if key in self.in_progress:
            raise VerificationInProgressError(coin)
        self.in_progress.add(key)
        try:
            yield
        finally:
            self.in_progress.discard(key)
