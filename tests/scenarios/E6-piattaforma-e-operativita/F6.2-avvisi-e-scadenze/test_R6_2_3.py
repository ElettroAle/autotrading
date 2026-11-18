"""R6.2.3: the alerts of every source in one list, opened with their notification by the worker and read, resolved and
counted through the use cases of the API, on the fake adapters (ADR avvisi-nel-contesto-delle-notifiche, ADR
api-degli-avvisi-e-link-nelle-notifiche). playwright-bdd runs the same scenarios on the pages of the dashboard.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.application.flows.confirm_reconciliation import ConfirmReconciliationCommand
from autotrading.application.flows.errors import FlowCredentialsRejectedError
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand, PauseAffectedFlowsUseCase
from autotrading.application.notifications.get_alert import GetAlertCommand
from autotrading.application.notifications.list_alerts import ListAlertsCommand
from autotrading.application.notifications.notify_reconciliation_alarm import NotifyReconciliationAlarmUseCase
from autotrading.application.notifications.resolve_alert import ResolveAlertCommand
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableKind
from autotrading.domain.notifications.alert import (
    Alert,
    AlertKind,
    AlertRemedy,
    AlertResourceKind,
    AlertSeverity,
    AlertState,
)
from autotrading.domain.notifications.alert_page import AlertFilter
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import READ_AT, a_fill, a_position, an_activity
from tests.support.flow_cycles import FlowCycles
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E6-piattaforma-e-operativita/F6.2-avvisi-e-scadenze/R6.2.3-centro-degli-avvisi.feature")

CHAT = ChatId(6230)
USDC = "USDC"
# The balance the account had at the previous reading, and the one an alarm reads beyond the threshold of 1%.
REFERENCE, READ_BEYOND = Decimal(1000), Decimal(980)


@dataclass
class Alerts:
    """The platform of the scenario, with what anna sees of her alerts."""

    cycles: FlowCycles = field(default_factory=FlowCycles)
    listed: list[Alert] = field(default_factory=list)
    detail: Alert | None = None
    alert_of_bruno: Alert | None = None

    @property
    def platform(self) -> Platform:
        return self.cycles.platform

    def tenant(self, user: str = "anna") -> TenantId:
        return self.platform.tenant_of(user)

    def use_cases(self, user: str = "anna") -> TenantUseCases:
        return self.platform.use_cases_of(user)

    def account(self, name: str) -> UUID:
        return self.cycles.account_of("anna", name)

    def address(self, flow: str) -> str:
        return self.cycles.credentials_of(flow).value("account_address")

    def all_alerts(self, user: str = "anna") -> list[Alert]:
        return list(self.use_cases(user).list_alerts.execute(ListAlertsCommand(AlertFilter())).alerts)

    def only(self, kind: AlertKind) -> Alert:
        [alert] = [alert for alert in self.all_alerts() if alert.cause.kind is kind]
        return alert

    def open_count(self) -> int:
        return self.use_cases().count_open_alerts.execute()

    def link_telegram(self, user: str = "anna") -> None:
        tenant_id = self.tenant(user)
        self.platform.chats[tenant_id] = LinkedChat(tenant_id, CHAT)

    def raise_alarm(self, account: str) -> None:
        """What the reconciliation of a cycle does with a balance beyond the threshold (R3.3.1)."""
        account_id, tenant_id = self.account(account), self.tenant()
        comparison = BalanceComparison(REFERENCE, READ_BEYOND, READ_AT)
        self.platform.readings.save_reading(AccountReading(account_id, READ_AT, {}, REFERENCE, comparison))
        assert self.platform.readings.open(ReconciliationAlarm.of(account_id, comparison))
        notice = NotifyReconciliationAlarmUseCase(
            self.platform.notify_for(tenant_id), self.platform.alerts_of(tenant_id), USDC
        )
        notice.execute(account_id, account, READ_BEYOND, REFERENCE)

    def pause_on_its_own(self, flow: str, user: str = "anna") -> None:
        """What the cycle does with a permanent error: it pauses the flows of the account and tells why (R1.2.4)."""
        paused = self.cycles.flow(flow)
        ports = self.cycles.ports_of(paused.tenant_id)
        error = FlowCredentialsRejectedError("test-1", paused.assigned_account_id, "API wallet scaduto")
        PauseAffectedFlowsUseCase(ports.flows, ports.pause, ports.flow_paused_notice).execute(
            PauseAffectedFlowsCommand.of_error(paused.id.value, error)
        )
        assert self.platform.alerts_of(self.tenant(user)).open_count() >= 1

    def end_cycle(self, flow: str) -> None:
        """The reconciliation at the end of a cycle of the flow, as the worker runs it."""
        ending = self.cycles.flow(flow)
        self.cycles.ports_of(ending.tenant_id).end_cycle.execute(ending.id.value, READ_AT, ())

    def open_page(self, criteria: AlertFilter) -> None:
        self.listed = list(self.use_cases().list_alerts.execute(ListAlertsCommand(criteria)).alerts)


@pytest.fixture
def alerts() -> Alerts:
    return Alerts()


# Given


@given(quoted('che "{user}" ha il conto "{account}" con il flusso attivo "{flow}"'))
def account_with_flow(alerts: Alerts, user: str, account: str, flow: str) -> None:
    alerts.cycles.add_flow(user, flow, account=account)


@given(quoted('che sul conto "{account}" è aperto un allarme di riconciliazione'))
def alarm_open(alerts: Alerts, account: str) -> None:
    alerts.raise_alarm(account)


@given(quoted('che il flusso "{flow}" è in pausa automatica'))
@given(quoted('che il flusso "{flow}" è in pausa automatica con un avviso aperto'))
def paused_on_its_own(alerts: Alerts, flow: str) -> None:
    alerts.pause_on_its_own(flow)


@given(quoted('che il saldo del conto "{account}" si discosta da quello atteso entro la soglia'))
def balance_within_threshold(alerts: Alerts, account: str) -> None:
    (flow,) = alerts.platform.flows.flows
    address = alerts.address(flow.name.value)
    reader = alerts.platform.activity_reader
    reader.activities[address] = an_activity(balance=REFERENCE)
    alerts.end_cycle(flow.name.value)
    # 0,5% of the balance of the previous reading: within the threshold of 1% the account has unless told.
    reader.activities[address] = an_activity(balance=Decimal(1005), read_at=READ_AT + timedelta(minutes=15))
    # A chat to tell: without it no notification could ever leave, whatever the cycle found.
    alerts.link_telegram()
    assert alerts.account(account) == flow.assigned_account_id


@given(quoted("che sul conto \"{account}\" è aperto l'avviso di un'esecuzione senza identificativo della piattaforma"))
def unattributable_fill_open(alerts: Alerts, account: str) -> None:
    (flow,) = alerts.platform.flows.flows
    address, reader = alerts.address(flow.name.value), alerts.platform.activity_reader
    alerts.end_cycle(flow.name.value)
    reader.executions[address] = [a_fill("ETH", None, executed_at=READ_AT + timedelta(minutes=1))]
    reader.activities[address] = an_activity(read_at=READ_AT + timedelta(minutes=2))
    alerts.end_cycle(flow.name.value)
    assert alerts.only(AlertKind.UNATTRIBUTABLE_FILL).cause.resource.resource_id == alerts.account(account)


@given(quoted('che "{user}" ha un avviso aperto e un avviso risolto'))
def one_open_one_resolved(alerts: Alerts, user: str) -> None:
    alerts.raise_alarm("test-1")
    alerts.use_cases(user).confirm_reconciliation.execute(ConfirmReconciliationCommand(alerts.account("test-1")))
    alerts.pause_on_its_own("alfa", user)


@given(quoted('che "{user}" ha collegato Telegram'))
def telegram_linked(alerts: Alerts, user: str) -> None:
    alerts.link_telegram(user)
    alerts.platform.links.dashboard = True


@given(quoted('che sul conto "{account}" c\'è un allarme di riconciliazione risolto'))
def alarm_resolved(alerts: Alerts, account: str) -> None:
    alerts.raise_alarm(account)
    alerts.use_cases().confirm_reconciliation.execute(ConfirmReconciliationCommand(alerts.account(account)))


@given(quoted('che "{user}" ha un avviso aperto'))
def other_user_alert(alerts: Alerts, user: str) -> None:
    alerts.cycles.add_flow(user, "beta", account="principale")
    alerts.pause_on_its_own("beta", user)
    [alerts.alert_of_bruno] = alerts.all_alerts(user)


# When


@when(quoted('"{user}" apre la pagina Avvisi'))
def open_alerts_page(alerts: Alerts, user: str) -> None:
    # The page opens on the open alerts (R6.2.3).
    assert user == "anna"
    alerts.open_page(AlertFilter(state=AlertState.OPEN))


@when(quoted('il flusso "{flow}" esegue un ciclo'))
def run_cycle(alerts: Alerts, flow: str) -> None:
    alerts.end_cycle(flow)


@when(quoted('"{user}" riprende il flusso "{flow}"'))
def resume(alerts: Alerts, user: str, flow: str) -> None:
    command = ChangeFlowStatusCommand(alerts.cycles.flow(flow).id, FlowAction.RESUME)
    alerts.use_cases(user).change_flow_status.execute(command)


@when(quoted('"{user}" apre il dettaglio dell\'avviso e conferma il saldo'))
def confirm_from_detail(alerts: Alerts, user: str) -> None:
    [listed] = alerts.all_alerts(user)
    detail = alerts.use_cases(user).get_alert.execute(GetAlertCommand(listed.id))
    assert AlertRemedy.CONFIRM_RECONCILIATION in detail.commands
    account_id = detail.cause.resource.resource_id
    alerts.use_cases(user).confirm_reconciliation.execute(ConfirmReconciliationCommand(account_id))
    alerts.detail = detail


@when(quoted('"{user}" segna l\'avviso come risolto'))
def resolve_by_hand(alerts: Alerts, user: str) -> None:
    alert = alerts.only(AlertKind.UNATTRIBUTABLE_FILL)
    alerts.use_cases(user).resolve_alert.execute(ResolveAlertCommand(alert.id))
    alerts.detail = alert


@when(quoted('"{user}" apre il dettaglio dell\'avviso'))
def open_detail(alerts: Alerts, user: str) -> None:
    [listed] = alerts.all_alerts(user)
    alerts.detail = alerts.use_cases(user).get_alert.execute(GetAlertCommand(listed.id))


@when("si apre l'avviso di una posizione su un asset di nessun flusso")
def position_of_no_flow(alerts: Alerts) -> None:
    (flow,) = alerts.platform.flows.flows
    alerts.platform.activity_reader.activities[alerts.address(flow.name.value)] = an_activity(
        positions=(a_position("SOL"),)
    )
    alerts.end_cycle(flow.name.value)


@when(quoted('"{user}" apre gli allarmi del conto "{account}" dal riquadro del conto'))
def open_account_alarms(alerts: Alerts, user: str, account: str) -> None:
    # The alarms of the account are its alerts in every state (R6.2.3).
    assert user == "anna"
    alerts.open_page(AlertFilter(resource_id=alerts.account(account)))


# Then


@then(
    quoted(
        'vede {count} avvisi aperti di gravità critica, uno con risorsa il conto "{account}" e uno con risorsa il '
        'flusso "{flow}"'
    )
)
def sees_critical_alerts(alerts: Alerts, count: str, account: str, flow: str) -> None:
    assert len(alerts.listed) == int(count)
    assert {(alert.state, alert.severity) for alert in alerts.listed} == {(AlertState.OPEN, AlertSeverity.CRITICAL)}
    resources = {(alert.cause.resource.kind, alert.cause.resource.name) for alert in alerts.listed}
    assert resources == {(AlertResourceKind.ACCOUNT, account), (AlertResourceKind.FLOW, flow)}


@then(quoted("la voce Avvisi del menu mostra {count}"))
def menu_shows(alerts: Alerts, count: str) -> None:
    assert alerts.open_count() == int(count)


@then("non si apre alcun avviso")
def no_alert(alerts: Alerts) -> None:
    # The cycle found the change: no alert means it opened none, not that nothing was found.
    kinds = [item.kind for item in alerts.platform.readings.items]
    assert kinds == [UnattributableKind.BALANCE_CHANGE]
    assert alerts.all_alerts() == []


@then(quoted('"{user}" non riceve alcuna notifica'))
def nothing_told(alerts: Alerts, user: str) -> None:
    assert alerts.platform.chats[alerts.tenant(user)].chat_id == CHAT
    assert alerts.platform.messenger.received_by(CHAT) == []


@then(quoted('l\'avviso del flusso "{flow}" è risolto'))
def flow_alert_resolved(alerts: Alerts, flow: str) -> None:
    alert = alerts.only(AlertKind.FLOW_PAUSED)
    assert (alert.cause.resource.name, alert.state) == (flow, AlertState.RESOLVED)


@then("la voce Avvisi del menu non mostra alcun numero")
def menu_shows_nothing(alerts: Alerts) -> None:
    assert alerts.open_count() == 0


@then("l'avviso è risolto")
def alert_resolved(alerts: Alerts) -> None:
    assert alerts.detail is not None
    assert alerts.use_cases().get_alert.execute(GetAlertCommand(alerts.detail.id)).state is AlertState.RESOLVED


@then("non c'è il comando per segnarlo come risolto")
def no_resolve_command(alerts: Alerts) -> None:
    assert alerts.detail is not None
    assert AlertRemedy.RESOLVE not in alerts.detail.commands


@then("c'è il comando per riprendere il flusso")
def resume_command(alerts: Alerts) -> None:
    assert alerts.detail is not None
    assert alerts.detail.commands == (AlertRemedy.RESUME_FLOW,)


@then("vede solo l'avviso aperto")
def sees_only_open(alerts: Alerts) -> None:
    assert [alert.state for alert in alerts.listed] == [AlertState.OPEN]


@then(quoted('scegliendo lo stato "{state}" vede entrambi'))
def sees_both(alerts: Alerts, state: str) -> None:
    assert state == "tutti"
    alerts.open_page(AlertFilter())
    assert sorted(alert.state for alert in alerts.listed) == [AlertState.OPEN, AlertState.RESOLVED]


@then("la notifica porta al dettaglio dell'avviso")
def leads_to_detail(alerts: Alerts) -> None:
    alert = alerts.only(AlertKind.UNATTRIBUTABLE_POSITION)
    target = NotificationTarget.alert(alert.id.value)
    link = NotificationLink(target.label, alerts.platform.links.address_of(target))
    assert alerts.platform.messenger.links_received_by(CHAT) == [(link,)]


@then(quoted('vede gli avvisi filtrati per il conto "{account}" con tutti gli stati'))
def sees_account_alerts(alerts: Alerts, account: str) -> None:
    assert [alert.cause.resource.name for alert in alerts.listed] == [account]
    assert [alert.state for alert in alerts.listed] == [AlertState.RESOLVED]


@then(quoted('l\'avviso di "{user}" non compare'))
def other_alert_absent(alerts: Alerts, user: str) -> None:
    assert alerts.alert_of_bruno is not None
    assert alerts.alert_of_bruno.id in [alert.id for alert in alerts.all_alerts(user)]
    assert alerts.alert_of_bruno.id not in [alert.id for alert in alerts.listed]
