from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.flows.list_reconciliation_alarms import (
    ListReconciliationAlarmsCommand,
    ListReconciliationAlarmsUseCase,
)
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT

ACCOUNT, OTHER = uuid4(), uuid4()


def alarm_at(account_id: UUID, hours: int) -> ReconciliationAlarm:
    comparison = BalanceComparison(Decimal(1000), Decimal(980), READ_AT + timedelta(hours=hours))
    return ReconciliationAlarm.of(account_id, comparison)


def test_the_alarms_of_the_account_come_from_the_most_recent() -> None:
    readings = InMemoryReconciliationRepositoryAdapter()
    older = alarm_at(ACCOUNT, 0).confirmed(READ_AT + timedelta(minutes=30))
    newer = alarm_at(ACCOUNT, 2)
    readings.alarms.extend([older, alarm_at(OTHER, 1), newer])
    use_case = ListReconciliationAlarmsUseCase(readings, FakeAccountThresholdsAdapter({ACCOUNT: "test-1"}))

    assert use_case.execute(ListReconciliationAlarmsCommand(ACCOUNT)) == [newer, older]


def test_an_account_the_tenant_does_not_have_is_not_found() -> None:
    use_case = ListReconciliationAlarmsUseCase(
        InMemoryReconciliationRepositoryAdapter(), FakeAccountThresholdsAdapter({ACCOUNT: "test-1"})
    )

    with pytest.raises(FlowAccountNotFoundError):
        use_case.execute(ListReconciliationAlarmsCommand(OTHER))
