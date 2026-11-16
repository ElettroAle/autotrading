"""The worker reached in process instead of over HTTP: the use case the worker runs to record the ledger of an
account, for the same tenant (ADR incasso-dei-profitti)."""

from uuid import UUID

from autotrading.application.flows.record_account_executions import (
    RecordAccountExecutionsCommand,
    RecordAccountExecutionsUseCase,
)


class FakeLedgerRecordingAdapter:
    def __init__(self, record_executions: RecordAccountExecutionsUseCase) -> None:
        self._record_executions = record_executions
        self.recorded: list[UUID] = []

    def record(self, account_id: UUID) -> None:
        self.recorded.append(account_id)
        self._record_executions.execute(RecordAccountExecutionsCommand(account_id))
