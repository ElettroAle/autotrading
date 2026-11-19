"""R6.2.2: the expiry of every key, read by the adapter or given by the user, told at 30, 7 and 1 days and on the day,
once per threshold, on Telegram and in the bell, with the alert of the key open until it is renewed; the flows of an
expired key go in pause. On the use cases of the API and of the worker, with the fake adapters (ADR
scadenza-delle-chiavi-letta-o-indicata, ADR controllo-giornaliero-delle-scadenze). playwright-bdd runs the scenarios of
the pages Chiavi and Conti on the dashboard (ADR scadenza-nelle-pagine-chiavi-e-conti).
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand
from autotrading.application.agent.provider_key_summary import ProviderKeySummary
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyCommand
from autotrading.application.agent.set_provider_key_expiry import SetProviderKeyExpiryCommand
from autotrading.application.notifications.list_inbox_notifications import ListInboxNotificationsCommand
from autotrading.application.sources.source_credentials_summary import SourceCredentialsSummary
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.key_expiry import KeyExpiry as AccountKeyExpiry
from autotrading.domain.agent.key_expiry import KeyExpiry as ProviderKeyExpiry
from autotrading.domain.agent.key_expiry import KeyExpiryStatus
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.notifications.alert import Alert, AlertKind, AlertSeverity
from autotrading.domain.notifications.alert_page import AlertFilter
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.sources.key_expiry import KeyExpiryStatus as SourceKeyExpiryStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flow_cycles import FlowCycles
from tests.support.notifications import chat_named
from tests.support.platform import Platform
from tests.support.source_keys import configure_paid, offer_paid_sentiment, use_paid_sentiment
from tests.support.steps import quoted

scenarios("E6-piattaforma-e-operativita/F6.2-avvisi-e-scadenze/R6.2.2-avviso-di-scadenza-delle-chiavi.feature")

MONTHS = {
    "novembre": 11,
    "dicembre": 12,
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
}
NEW_KEY = {"api_key": "K-OPENROUTER-RENEWED"}


def day_of(text: str) -> date:
    """«15 dicembre 2026», as the scenarios write a day."""
    day, month, year = text.split()
    return date(int(year), MONTHS[month], int(day))


def heading_of(notice: str, key: str) -> str:
    """«la chiave openrouter scade domani» as the notification heads it: the key, then what happens to it."""
    return notice.removeprefix("la ").replace(f"chiave {key} ", f"chiave {key}: ", 1)


@dataclass
class Expiries:
    """The worker and the API of anna, with the flows that use her key and her chat on Telegram."""

    cycles: FlowCycles = field(default_factory=FlowCycles)
    key: str = "openrouter"
    seen: ProviderKeySummary | None = None
    # The adapter of a source the scenario configured, and what the section Fonti showed of it (R4.1.2).
    source_adapter: str | None = None
    source_seen: SourceCredentialsSummary | None = None

    @property
    def platform(self) -> Platform:
        return self.cycles.platform

    def tenant(self) -> TenantId:
        return self.platform.tenant_of("anna")

    def use_cases(self) -> TenantUseCases:
        return self.platform.use_cases_of("anna")

    def on(self, day: date) -> None:
        """The day of the worker and of the API, in the morning of the daily check."""
        instant = datetime(day.year, day.month, day.day, 6, 0, tzinfo=UTC)
        self.cycles.clock.current = instant
        self.platform.now = instant

    def check(self) -> None:
        self.platform.check_key_expiries(self.tenant())

    def expires_on(self, day: date) -> None:
        self.use_cases().set_provider_key_expiry.execute(SetProviderKeyExpiryCommand(self.key, day))

    def summary(self) -> ProviderKeySummary:
        [summary] = [each for each in self.use_cases().list_provider_keys.execute() if each.provider.value == self.key]
        return summary

    def source_summary(self) -> SourceCredentialsSummary | None:
        if self.source_adapter is None:
            return None
        summaries = self.use_cases().list_source_credentials.execute()
        [summary] = [each for each in summaries if each.adapter == self.source_adapter]
        return summary

    def telegram(self) -> list[str]:
        return self.platform.messenger.received_by(chat_named("anna"))

    def bell(self) -> list[str]:
        page = self.use_cases().list_inbox_notifications.execute(ListInboxNotificationsCommand())
        return [notification.title for notification in page.notifications]

    def notices_told(self, heading: str) -> list[str]:
        return [text for text in self.telegram() if heading in text.splitlines()[0]]

    def key_alerts(self) -> list[Alert]:
        alerts = self.platform.alerts_of(self.tenant()).list(AlertFilter(), None).alerts
        return [alert for alert in alerts if alert.cause.resource.name == self.key]

    def flow(self, name: str) -> Flow:
        return self.cycles.flow(name)

    def account_id(self) -> AccountId:
        account_id = self.flow("alfa").account_id
        assert account_id is not None
        return AccountId(account_id)


@pytest.fixture
def expiries() -> Expiries:
    return Expiries()


# Given


@given(quoted('che "{user}" ha la chiave del fornitore IA "{key}" usata dai flussi "{first}" e "{second}"'))
def key_used_by_flows(expiries: Expiries, user: str, key: str, first: str, second: str) -> None:
    for name in (first, second):
        expiries.cycles.add_flow(user, name)
    expiries.platform.chats[expiries.tenant()] = LinkedChat(expiries.tenant(), chat_named(user))
    assert {flow.model_provider for flow in expiries.platform.flows.flows} == {key}
    assert expiries.summary().expiry is None


@given(quoted('che "{user}" ha un conto "{exchange}" il cui API wallet è valido fino al {day}'))
def wallet_valid_until(expiries: Expiries, user: str, exchange: str, day: str) -> None:
    account = expiries.platform.account_named(user, "test-1")
    assert account.exchange.value == exchange
    expiries.platform.hyperliquid.reads_expiry = True
    expiries.platform.hyperliquid.valid_until(expiries.cycles.credentials_of("alfa"), day_of(day))
    assert account.expiry is None


@given(quoted('che la chiave "{key}" scade il {day}'))
def key_expires_on(expiries: Expiries, key: str, day: str) -> None:
    expiries.key = key
    expiries.expires_on(day_of(day))


@given(quoted('che "{user}" ha già ricevuto l\'avviso a 7 giorni per la chiave "{key}"'))
def already_told_seven_days(expiries: Expiries, user: str, key: str) -> None:
    assert user == "anna"
    expiries.key = key
    expiries.expires_on(date(2026, 12, 15))
    expiries.on(date(2026, 12, 8))
    expiries.check()
    assert len(expiries.notices_told(f"chiave {key}: scade tra 7 giorni")) == 1


@given(quoted('che la chiave "{key}" è scaduta'))
def key_expired(expiries: Expiries, key: str) -> None:
    expiries.key = key
    expiries.expires_on(date(2026, 12, 1))
    expiries.on(date(2026, 12, 15))
    assert expiries.summary().reading.status is KeyExpiryStatus.EXPIRED


@given(quoted('che la chiave "{key}" scade tra 5 giorni e "{user}" ha ricevuto l\'avviso a 7 giorni'))
def expires_in_five_days_and_told(expiries: Expiries, key: str, user: str) -> None:
    assert user == "anna"
    expiries.key = key
    expiries.expires_on(date(2026, 12, 15))
    expiries.on(date(2026, 12, 10))
    expiries.check()
    assert expiries.notices_told(f"chiave {key}: scade tra 5 giorni")
    assert expiries.summary().reading.days_left == 5


@given(quoted('che la chiave "{key}" scade tra {days} giorni'))
def expires_in_days(expiries: Expiries, key: str, days: str) -> None:
    expiries.key = key
    expiries.on(date(2026, 11, 25))
    expiries.expires_on(date(2026, 12, 15))
    assert expiries.summary().reading.days_left == int(days)


@given("che la chiave di un adapter di fonte non ha una data di scadenza")
def source_key_without_expiry(expiries: Expiries) -> None:
    expiries.source_adapter = "LunarCrush"
    offer_paid_sentiment(expiries.cycles, expiries.source_adapter)
    configure_paid(expiries.cycles, "anna", expiries.source_adapter)
    use_paid_sentiment(expiries.cycles, "alfa", expiries.source_adapter)
    summary = expiries.source_summary()
    assert summary is not None
    assert summary.expiry is None


# When


@when("la piattaforma verifica le credenziali del conto")
def verifies_credentials(expiries: Expiries) -> None:
    worker = expiries.platform.worker_for(expiries.tenant())
    worker.read_exchange_state.execute(ReadExchangeStateCommand(expiries.account_id()))


@when(quoted('"{user}" indica per la chiave "{key}" la scadenza {day}'))
def gives_expiry(expiries: Expiries, user: str, key: str, day: str) -> None:
    assert user == "anna"
    expiries.key = key
    expiries.expires_on(day_of(day))


@when(parsers.parse("è il {day}"))
def is_the_day(expiries: Expiries, day: str) -> None:
    expiries.on(day_of(day.strip()))
    expiries.check()


@when("la piattaforma ricontrolla le scadenze lo stesso giorno")
def checks_again(expiries: Expiries) -> None:
    expiries.check()


@when(quoted('arriva il ciclo del flusso "{flow}"'))
def cycle_arrives(expiries: Expiries, flow: str) -> None:
    expiries.cycles.run(flow)


@when(quoted('"{user}" sostituisce la chiave con una che scade il {day}'))
def replaces_key(expiries: Expiries, user: str, day: str) -> None:
    assert user == "anna"
    command = ReplaceProviderKeyCommand(expiries.key, NEW_KEY, day_of(day))
    expiries.use_cases().replace_provider_key.execute(command)


@when("la piattaforma controlla le scadenze")
def checks(expiries: Expiries) -> None:
    expiries.check()


@when(quoted('"{user}" apre la pagina Chiavi'))
def opens_keys_page(expiries: Expiries, user: str) -> None:
    assert user == "anna"
    expiries.seen = expiries.summary()
    expiries.source_seen = expiries.source_summary()


# Then


@then(quoted("il conto mostra la scadenza {day}"))
def account_shows_expiry(expiries: Expiries, day: str) -> None:
    account = expiries.use_cases().get_account.execute(GetAccountCommand(expiries.account_id()))
    assert account.expiry.expiry == AccountKeyExpiry.read(day_of(day))
    assert not account.expiry.editable


@then(quoted("la chiave mostra la scadenza {day}"))
def key_shows_expiry(expiries: Expiries, day: str) -> None:
    summary = expiries.summary()
    assert summary.expiry == ProviderKeyExpiry.entered(day_of(day))
    assert summary.expiry_editable


@then(quoted('"{user}" riceve su Telegram e nel campanello l\'avviso "{notice}" con i flussi "{first}" e "{second}"'))
def receives_notice(expiries: Expiries, user: str, notice: str, first: str, second: str) -> None:
    assert user == "anna"
    heading = heading_of(notice, expiries.key)
    [told] = expiries.notices_told(heading)
    assert f"Flussi: {first}, {second}" in told.splitlines()
    assert "Scadenza: 15/12/2026" in told.splitlines()
    assert heading in expiries.bell()


@then(quoted('"{user}" non riceve un secondo avviso a 7 giorni'))
def no_second_notice(expiries: Expiries, user: str) -> None:
    assert user == "anna"
    assert len(expiries.notices_told(f"chiave {expiries.key}: scade tra 7 giorni")) == 1
    assert expiries.bell().count(f"chiave {expiries.key}: scade tra 7 giorni") == 1


@then(quoted('il flusso "{flow}" è in pausa con il motivo "{reason}"'))
def flow_paused(expiries: Expiries, flow: str, reason: str) -> None:
    paused = expiries.flow(flow)
    assert paused.status is FlowStatus.PAUSED
    assert expiries.platform.flows.pause_reasons[paused.id] == reason
    # The cycle did not start: no model was asked with the expired key.
    assert expiries.cycles.model.calls == []


@then("l'avviso nelle pagine Chiavi e Conti sparisce")
def notice_gone_from_pages(expiries: Expiries) -> None:
    assert expiries.summary().reading.status is KeyExpiryStatus.VALID
    accounts = expiries.use_cases().list_accounts.execute()
    assert {account.expiry.reading.status.value for account in accounts} == {"unknown"}


@then(quoted('"{user}" riceverà di nuovo gli avvisi a 30, 7 e 1 giorno dalla nuova scadenza'))
def told_again(expiries: Expiries, user: str) -> None:
    assert user == "anna"
    headings = {
        date(2027, 2, 13): "scade tra 30 giorni",
        date(2027, 3, 8): "scade tra 7 giorni",
        date(2027, 3, 14): "scade domani",
    }
    for day, headline in headings.items():
        expiries.on(day)
        expiries.check()
        assert len(expiries.notices_told(f"chiave {expiries.key}: {headline}")) == 1


@then(quoted('la chiave mostra "{state}" e non genera avvisi'))
def unknown_and_silent(expiries: Expiries, state: str) -> None:
    assert state == "scadenza sconosciuta"
    assert expiries.seen is not None
    assert expiries.seen.reading.status is KeyExpiryStatus.UNKNOWN
    if expiries.source_adapter is not None:
        assert expiries.source_seen is not None
        assert expiries.source_seen.reading.status is SourceKeyExpiryStatus.UNKNOWN
    expiries.check()
    assert expiries.telegram() == []
    assert expiries.bell() == []
    assert expiries.platform.alerts_of(expiries.tenant()).list(AlertFilter(), None).alerts == ()


@then(quoted('il centro degli avvisi ha un avviso aperto "{severity}" per la chiave "{key}"'))
def open_alert(expiries: Expiries, severity: str, key: str) -> None:
    assert severity == "attenzione"
    [alert] = [alert for alert in expiries.key_alerts() if alert.is_open]
    assert (alert.cause.resource.name, alert.severity, alert.cause.kind) == (
        key,
        AlertSeverity.WARNING,
        AlertKind.KEY_EXPIRING,
    )


@then(quoted('quando la chiave è scaduta l\'avviso diventa "{severity}"'))
def alert_becomes_critical(expiries: Expiries, severity: str) -> None:
    assert severity == "critica"
    expiries.on(date(2026, 12, 15))
    expiries.check()
    [alert] = [alert for alert in expiries.key_alerts() if alert.is_open]
    assert (alert.severity, alert.cause.kind) == (AlertSeverity.CRITICAL, AlertKind.KEY_EXPIRED)


@then(quoted('quando "{user}" sostituisce la chiave con una che scade tra {days} giorni l\'avviso è risolto'))
def renewal_resolves(expiries: Expiries, user: str, days: str) -> None:
    assert (user, days) == ("anna", "90")
    command = ReplaceProviderKeyCommand(expiries.key, NEW_KEY, date(2027, 3, 15))
    expiries.use_cases().replace_provider_key.execute(command)
    expiries.check()
    assert expiries.summary().reading.days_left == int(days)
    assert [alert.is_open for alert in expiries.key_alerts()] == [False, False]
