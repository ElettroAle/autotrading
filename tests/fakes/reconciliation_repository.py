"""Fake of the readings of the accounts and of the unattributable items, recorded once like the database does."""

from uuid import UUID

from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind


class InMemoryReconciliationRepositoryAdapter:
    def __init__(self) -> None:
        self.readings: dict[UUID, AccountReading] = {}
        self.items: list[UnattributableItem] = []
        self.resolved: list[UnattributableItem] = []

    def last_reading(self, account_id: UUID) -> AccountReading | None:
        return self.readings.get(account_id)

    def save_reading(self, reading: AccountReading) -> None:
        self.readings[reading.account_id] = reading

    def record(self, item: UnattributableItem) -> bool:
        if any(_same_case(item, recorded) for recorded in self.items):
            return False
        self.items.append(item)
        return True

    def resolve_positions(self, account_id: UUID, open_assets: frozenset[str]) -> None:
        closed = [
            item
            for item in self.items
            if item.account_id == account_id
            and item.kind is UnattributableKind.POSITION
            and item.reference not in open_assets
        ]
        self.items = [item for item in self.items if item not in closed]
        self.resolved.extend(closed)


def _same_case(item: UnattributableItem, recorded: UnattributableItem) -> bool:
    return (item.account_id, item.kind, item.reference) == (recorded.account_id, recorded.kind, recorded.reference)
