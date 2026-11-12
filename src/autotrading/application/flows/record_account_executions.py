from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from autotrading.application.flows.errors import FlowLedgerIncompleteError
from autotrading.application.flows.ports import (
    AccountExecutionsPort,
    FlowLedgerPort,
    FlowRepositoryPort,
    PlatformOrdersPort,
)
from autotrading.domain.flows.ledger import AccountLedger, LedgerEntry, LedgerKeys

# The exchange may publish an execution or a funding payment after a later one, and funding is paid at the turn of
# every hour: the window starts an hour before the cursor, and what is recorded already is read once (ADR 0076).
OVERLAP = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class RecordAccountExecutionsCommand:
    account_id: UUID


class RecordAccountExecutionsUseCase:
    """At every cycle, before anything reads the flows of the account: what the exchange added to the account since
    the last time enters the ledger, each execution given to its flow and added to its totals (ADR 0063).

    Only what is new is read and written: the cycle never reads the whole history, of the exchange or of the ledger.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        executions: AccountExecutionsPort,
        orders: PlatformOrdersPort,
        ledger: FlowLedgerPort,
    ) -> None:
        self._flows = flows
        self._executions = executions
        self._orders = orders
        self._ledger = ledger

    def execute(self, command: RecordAccountExecutionsCommand) -> tuple[LedgerEntry, ...]:
        account_id = command.account_id
        cursor = self._ledger.cursor(account_id)
        since = None if cursor is None else cursor - OVERLAP
        window = self._executions.since(account_id, since)
        if not window.complete:
            raise FlowLedgerIncompleteError(account_id)
        known = LedgerKeys() if since is None else self._ledger.recorded_since(account_id, since)
        unknown = known.unknown_in(window)
        flows = [flow for flow in self._flows.list() if flow.account_id == account_id]
        ledger = AccountLedger.attributed(
            flows,
            unknown,
            self._orders.orders_among(account_id, unknown.order_ids),
            self._ledger.totals_of(flow.id for flow in flows),
        )
        latest = ledger.latest
        if latest is None:
            return ()
        return self._ledger.record(account_id, ledger, latest)
