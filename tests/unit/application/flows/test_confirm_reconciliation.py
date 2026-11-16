from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.confirm_reconciliation import (
    ConfirmReconciliationCommand,
    ConfirmReconciliationUseCase,
)
from autotrading.application.flows.errors import FlowAccountNotFoundError, ReconciliationAlarmNotOpenError
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT

ACCOUNT = uuid4()
CONFIRMED_AT = READ_AT + timedelta(hours=1)
COMPARISON = BalanceComparison(Decimal(1000), Decimal(980), READ_AT)


class Bench:
    def __init__(self) -> None:
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.use_case = ConfirmReconciliationUseCase(
            self.readings, FakeAccountThresholdsAdapter({ACCOUNT: "test-1"}), lambda: CONFIRMED_AT
        )

    def alarm_beyond_the_threshold(self) -> None:
        self.readings.save_reading(AccountReading(ACCOUNT, READ_AT, {}, Decimal(1000), COMPARISON))
        self.readings.open(ReconciliationAlarm.of(ACCOUNT, COMPARISON))


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_confirmation_closes_the_alarm_with_its_moment(bench: Bench) -> None:
    bench.alarm_beyond_the_threshold()

    bench.use_case.execute(ConfirmReconciliationCommand(ACCOUNT))

    assert bench.readings.open_alarm(ACCOUNT) is None
    assert [alarm.confirmed_at for alarm in bench.readings.alarms] == [CONFIRMED_AT]


def test_the_confirmation_takes_the_balance_read_as_the_new_reference(bench: Bench) -> None:
    bench.alarm_beyond_the_threshold()

    bench.use_case.execute(ConfirmReconciliationCommand(ACCOUNT))

    assert bench.readings.readings[ACCOUNT].reference_balance == Decimal(980)


def test_an_alarm_without_reading_is_closed_all_the_same(bench: Bench) -> None:
    bench.readings.open(ReconciliationAlarm.of(ACCOUNT, COMPARISON))

    bench.use_case.execute(ConfirmReconciliationCommand(ACCOUNT))

    assert bench.readings.open_alarm(ACCOUNT) is None
    assert bench.readings.readings == {}


def test_an_account_without_an_open_alarm_refuses_the_confirmation(bench: Bench) -> None:
    bench.readings.save_reading(AccountReading(ACCOUNT, READ_AT, {}, Decimal(1000), COMPARISON))

    with pytest.raises(ReconciliationAlarmNotOpenError) as raised:
        bench.use_case.execute(ConfirmReconciliationCommand(ACCOUNT))

    assert str(raised.value) == "il conto test-1 non ha un allarme di riconciliazione aperto"
    assert raised.value.status_code == 409
    assert bench.readings.readings[ACCOUNT].reference_balance == Decimal(1000)


def test_an_account_the_tenant_does_not_have_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowAccountNotFoundError):
        bench.use_case.execute(ConfirmReconciliationCommand(uuid4()))
