from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.flows.read_account_reconciliation import (
    AccountReconciliationStatus,
    ReadAccountReconciliationCommand,
    ReadAccountReconciliationUseCase,
)
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT

ACCOUNT = uuid4()
COMPARISON = BalanceComparison(Decimal(1000), Decimal(980), READ_AT)


class Bench:
    def __init__(self) -> None:
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.thresholds = FakeAccountThresholdsAdapter({ACCOUNT: "test-1"})
        self.use_case = ReadAccountReconciliationUseCase(self.readings, self.thresholds)


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_status_has_the_last_comparison_the_threshold_and_the_open_alarm(bench: Bench) -> None:
    alarm = ReconciliationAlarm.of(ACCOUNT, COMPARISON)
    bench.thresholds.thresholds[ACCOUNT] = Decimal(3)
    bench.readings.save_reading(AccountReading(ACCOUNT, READ_AT, {}, Decimal(1000), COMPARISON))
    bench.readings.open(alarm)

    status = bench.use_case.execute(ReadAccountReconciliationCommand(ACCOUNT))

    assert status == AccountReconciliationStatus(Decimal(3), COMPARISON, alarm)


def test_an_account_never_compared_has_only_its_threshold(bench: Bench) -> None:
    status = bench.use_case.execute(ReadAccountReconciliationCommand(ACCOUNT))

    assert status == AccountReconciliationStatus(Decimal(1), None, None)


def test_an_account_the_tenant_does_not_have_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowAccountNotFoundError):
        bench.use_case.execute(ReadAccountReconciliationCommand(uuid4()))


def test_an_account_is_aligned_without_an_open_alarm() -> None:
    assert AccountReconciliationStatus(Decimal(1), COMPARISON, None).aligned is True
    alarm = ReconciliationAlarm.of(ACCOUNT, COMPARISON)
    assert AccountReconciliationStatus(Decimal(1), COMPARISON, alarm).aligned is False
