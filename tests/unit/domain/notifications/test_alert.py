from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.notifications.alert import (
    Alert,
    AlertCause,
    AlertId,
    AlertKind,
    AlertRemedy,
    AlertResource,
    AlertResourceKind,
    AlertSeverity,
    AlertState,
)
from autotrading.domain.notifications.errors import AlertNotResolvableByHandError, InvalidAlertError
from autotrading.domain.notifications.notification import Amount, NotificationLine

ACCOUNT_ID, FLOW_ID = uuid4(), uuid4()
OPENED_AT = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
RESOLVED_AT = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)


def alert_of(cause: AlertCause, resolved_at: datetime | None = None) -> Alert:
    return Alert(AlertId.new(), cause, OPENED_AT, resolved_at)


def test_an_alarm_of_reconciliation_is_critical_on_the_account_with_both_balances() -> None:
    cause = AlertCause.reconciliation_alarm(
        ACCOUNT_ID, "test-1", Amount(Decimal(980), "USDC"), Amount(Decimal(1000), "USDC")
    )

    assert cause.kind.severity is AlertSeverity.CRITICAL
    assert cause.resource == AlertResource(AlertResourceKind.ACCOUNT, ACCOUNT_ID, "test-1")
    assert cause.values == (
        NotificationLine("Saldo letto", "980 USDC"),
        NotificationLine("Saldo atteso", "1000 USDC"),
    )


def test_a_flow_paused_on_its_own_is_critical_on_the_flow_with_the_reason() -> None:
    cause = AlertCause.flow_paused(FLOW_ID, "alfa", "credito esaurito")

    assert cause.kind.severity is AlertSeverity.CRITICAL
    assert cause.resource == AlertResource(AlertResourceKind.FLOW, FLOW_ID, "alfa")
    assert cause.values == (NotificationLine("Motivo", "credito esaurito"),)


@pytest.mark.parametrize("kind", [AlertKind.UNATTRIBUTABLE_POSITION, AlertKind.UNATTRIBUTABLE_FILL])
def test_a_case_no_flow_explains_asks_attention_on_the_account_with_its_asset(kind: AlertKind) -> None:
    factories = {
        AlertKind.UNATTRIBUTABLE_POSITION: AlertCause.unattributable_position,
        AlertKind.UNATTRIBUTABLE_FILL: AlertCause.unattributable_fill,
    }

    cause = factories[kind](ACCOUNT_ID, "test-1", "SOL")

    assert cause.kind is kind
    assert kind.severity is AlertSeverity.WARNING
    assert cause.resource == AlertResource(AlertResourceKind.ACCOUNT, ACCOUNT_ID, "test-1")
    assert cause.values == (NotificationLine("Asset", "SOL"),)


def test_the_key_of_the_cause_names_the_kind_the_resource_and_the_asset() -> None:
    position = AlertCause.unattributable_position(ACCOUNT_ID, "test-1", "SOL")
    other_asset = AlertCause.unattributable_position(ACCOUNT_ID, "test-1", "ETH")
    fill = AlertCause.unattributable_fill(ACCOUNT_ID, "test-1", "SOL")

    assert position.key == AlertKind.UNATTRIBUTABLE_POSITION.cause_key(ACCOUNT_ID, "SOL")
    assert len({position.key, other_asset.key, fill.key}) == 3
    assert AlertCause.flow_paused(FLOW_ID, "alfa", "a").key == AlertCause.flow_paused(FLOW_ID, "alfa", "b").key


def test_a_cause_on_a_resource_of_another_kind_does_not_exist() -> None:
    with pytest.raises(InvalidAlertError):
        AlertCause(AlertKind.FLOW_PAUSED, AlertResource(AlertResourceKind.ACCOUNT, ACCOUNT_ID, "test-1"), ())


def test_a_resource_without_a_name_does_not_exist() -> None:
    with pytest.raises(InvalidAlertError):
        AlertResource(AlertResourceKind.FLOW, FLOW_ID, " ")


def test_the_kinds_of_a_severity_are_those_that_declare_it() -> None:
    assert AlertKind.of_severity(AlertSeverity.CRITICAL) == frozenset(
        {AlertKind.RECONCILIATION_ALARM, AlertKind.FLOW_PAUSED}
    )
    assert AlertKind.of_severity(AlertSeverity.WARNING) == frozenset(
        {AlertKind.UNATTRIBUTABLE_POSITION, AlertKind.UNATTRIBUTABLE_FILL}
    )


def test_every_kind_has_a_heading() -> None:
    assert [kind.heading for kind in AlertKind] == [
        "Allarme di riconciliazione",
        "Flusso in pausa automatica",
        "Posizione su un asset di nessun flusso",
        "Esecuzione senza identificativo della piattaforma",
    ]


def test_an_open_alert_offers_the_command_that_removes_its_cause() -> None:
    alarm = alert_of(
        AlertCause.reconciliation_alarm(ACCOUNT_ID, "test-1", Amount(Decimal(1), "USDC"), Amount(Decimal(2), "USDC"))
    )
    paused = alert_of(AlertCause.flow_paused(FLOW_ID, "alfa", "credito esaurito"))
    position = alert_of(AlertCause.unattributable_position(ACCOUNT_ID, "test-1", "SOL"))
    fill = alert_of(AlertCause.unattributable_fill(ACCOUNT_ID, "test-1", "SOL"))

    assert alarm.commands == (AlertRemedy.CONFIRM_RECONCILIATION,)
    assert paused.commands == (AlertRemedy.RESUME_FLOW,)
    assert position.commands == ()
    assert fill.commands == (AlertRemedy.RESOLVE,)


def test_a_resolved_alert_offers_no_command_and_says_when() -> None:
    fill = alert_of(AlertCause.unattributable_fill(ACCOUNT_ID, "test-1", "SOL"), RESOLVED_AT)

    assert fill.commands == ()
    assert fill.state is AlertState.RESOLVED
    assert not fill.is_open
    assert fill.severity is AlertSeverity.WARNING


def test_an_open_alert_is_open() -> None:
    assert alert_of(AlertCause.flow_paused(FLOW_ID, "alfa", "x")).state is AlertState.OPEN


def test_only_an_alert_without_an_automatic_resolution_is_resolved_by_hand() -> None:
    alert_of(AlertCause.unattributable_fill(ACCOUNT_ID, "test-1", "SOL")).require_resolvable_by_hand()

    with pytest.raises(AlertNotResolvableByHandError) as raised:
        alert_of(AlertCause.flow_paused(FLOW_ID, "alfa", "x")).require_resolvable_by_hand()

    assert raised.value.status_code == 409
    assert raised.value.details == {"kind": "flow_paused"}


def test_an_alert_id_is_new_every_time() -> None:
    first, second = AlertId.new(), AlertId.new()

    assert first != second
