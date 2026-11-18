"""Fake of the readings of the accounts, of the unattributable items and of the alarms of reconciliation, recorded once
like the database does."""

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.flows.unattributable_page import (
    RecordedUnattributable,
    UnattributableCursor,
    UnattributableFilter,
    UnattributablePage,
)


class InMemoryReconciliationRepositoryAdapter:
    def __init__(self) -> None:
        self.readings: dict[UUID, AccountReading] = {}
        self.items: list[UnattributableItem] = []
        self.resolved: list[UnattributableItem] = []
        self.alarms: list[ReconciliationAlarm] = []

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

    def unattributable_of(
        self, account_id: UUID, criteria: UnattributableFilter, cursor: UnattributableCursor | None
    ) -> UnattributablePage:
        recorded = [_recorded(item) for item in [*self.items, *self.resolved] if item.account_id == account_id]
        admitted = sorted(
            (case for case in recorded if criteria.admits(case)), key=lambda case: case.cursor, reverse=True
        )
        after = [case for case in admitted if cursor is None or case.cursor < cursor]
        net_change = UnattributablePage.net_change_of(admitted)
        return UnattributablePage.of(after[: criteria.limit + 1], criteria.limit, len(admitted), net_change)

    def open_alarm(self, account_id: UUID) -> ReconciliationAlarm | None:
        return next((alarm for alarm in self.alarms if alarm.account_id == account_id and alarm.is_open), None)

    def open(self, alarm: ReconciliationAlarm) -> bool:
        if self.open_alarm(alarm.account_id) is not None:
            return False
        self.alarms.append(alarm)
        return True

    def confirm(self, account_id: UUID, at: datetime) -> bool:
        alarm = self.open_alarm(account_id)
        if alarm is None:
            return False
        self.alarms[self.alarms.index(alarm)] = alarm.confirmed(at)
        return True

    def alarms_of(self, account_id: UUID) -> list[ReconciliationAlarm]:
        of_account = [alarm for alarm in self.alarms if alarm.account_id == account_id]
        return sorted(of_account, key=lambda alarm: alarm.opened_at, reverse=True)


def _recorded(item: UnattributableItem) -> RecordedUnattributable:
    """The same key for the same case at every reading, as the database keeps the row it recorded once."""
    key = uuid5(NAMESPACE_URL, f"{item.account_id}/{item.kind.name}/{item.reference}/{item.detected_at.isoformat()}")
    return RecordedUnattributable(key, item)


def _same_case(item: UnattributableItem, recorded: UnattributableItem) -> bool:
    return (item.account_id, item.kind, item.reference) == (recorded.account_id, recorded.kind, recorded.reference)
