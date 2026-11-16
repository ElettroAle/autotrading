from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.openings_suspension import OpeningsSuspension, OpeningsSuspensionCause
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from tests.support.activity import READ_AT

ACCOUNT = uuid4()


def an_alarm() -> ReconciliationAlarm:
    return ReconciliationAlarm.of(ACCOUNT, BalanceComparison(Decimal(1000), Decimal(980), READ_AT))


def test_an_alarm_keeps_the_balances_and_the_deviation_of_its_comparison() -> None:
    alarm = an_alarm()

    assert (alarm.account_id, alarm.expected_balance, alarm.read_balance, alarm.deviation_percent) == (
        ACCOUNT,
        Decimal(1000),
        Decimal(980),
        Decimal(2),
    )
    assert alarm.opened_at == READ_AT


def test_an_alarm_is_open_until_confirmed() -> None:
    alarm = an_alarm()
    confirmed = alarm.confirmed(READ_AT + timedelta(hours=1))

    assert alarm.is_open
    assert not confirmed.is_open
    assert confirmed.confirmed_at == READ_AT + timedelta(hours=1)


def test_the_openings_of_the_account_are_suspended_with_its_name_since_the_alarm() -> None:
    alarm = an_alarm()

    suspension = alarm.suspension("test-1")

    assert suspension == OpeningsSuspension(
        "allarme di riconciliazione sul conto test-1", alarm.opened_at, OpeningsSuspensionCause.RECONCILIATION
    )
    assert not suspension.resumable
    assert suspension.blocked_reason == "allarme di riconciliazione sul conto test-1"
