from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from uuid import UUID

from autotrading.application.flows.errors import AssetUnderVerificationError
from tests.fakes.verification_run_repository import RunningVerifications


class InMemoryRunningVerificationsAdapter:
    """The procedures in progress the runs of the worker hold, as the API sees them before a flow starts."""

    def __init__(self, in_progress: RunningVerifications) -> None:
        self._in_progress = in_progress
        self.kept_free_while: list[frozenset[str]] = []

    @contextmanager
    def kept_free(self, account_id: UUID, assets: Iterable[str]) -> Iterator[None]:
        wanted = frozenset(assets)
        busy = sorted(asset for asset in wanted if (account_id, asset) in self._in_progress)
        if busy:
            raise AssetUnderVerificationError(busy[0])
        self.kept_free_while.append(wanted)
        yield
