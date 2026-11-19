"""R4.1.2: the credentials of an adapter of a source, given once per tenant and sealed, read only by the worker; an
adapter without them is not activatable, and one the provider refuses is an absent source told once. On the use cases
of the API and of the worker, with the fake adapters (ADR credenziali-degli-adapter-delle-fonti). playwright-bdd runs
the scenarios of the section Fonti on the dashboard (ADR sezione-fonti-nella-pagina-chiavi).
"""

from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.adapters.inbound.api.source_credentials import SourceCredentialsResponse
from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.ports import AdapterRequest
from autotrading.application.notifications.list_inbox_notifications import ListInboxNotificationsCommand
from autotrading.application.sources.source_credentials_summary import SourceCredentialsSummary
from autotrading.domain.notifications.linked_chat import LinkedChat
from tests.fakes.sources import FakeSentimentAdapter
from tests.support.flow_cycles import FlowCycles
from tests.support.lifecycle_steps import Lifecycle, modify
from tests.support.notifications import chat_named
from tests.support.source_keys import API_KEY, SENTIMENT, configure_paid, offer_paid_sentiment, use_paid_sentiment
from tests.support.steps import quoted

scenarios(
    "E4-replay-e-analisi/F4.1-fonti-ad-adapter-configurabili/R4.1.2-credenziali-degli-adapter-delle-fonti.feature"
)

TYPED_KEY = "K-LUNAR-SEGRETA"


@dataclass
class SourceKeys:
    """The page of the keys of the users, the paid adapter of the platform and what the section Fonti showed."""

    cycles: FlowCycles = field(default_factory=FlowCycles)
    lifecycle: Lifecycle = field(default_factory=Lifecycle)
    paid: FakeSentimentAdapter | None = None
    seen: list[SourceCredentialsSummary] = field(default_factory=list)

    def adapter(self) -> FakeSentimentAdapter:
        assert self.paid is not None
        return self.paid

    def section(self, user: str) -> list[SourceCredentialsSummary]:
        return self.cycles.platform.use_cases_of(user).list_source_credentials.execute()

    def summary(self, user: str, adapter: str) -> SourceCredentialsSummary:
        [summary] = [each for each in self.section(user) if each.adapter == adapter]
        return summary


@pytest.fixture
def keys() -> SourceKeys:
    return SourceKeys()


# Given


@given(quoted('che "{user}" è nella pagina delle chiavi'))
def on_keys_page(keys: SourceKeys, user: str) -> None:
    keys.cycles.add_flow(user, "alfa", sources=(SENTIMENT,))


@given(quoted('che esiste un adapter di fonte "{adapter}" che richiede una "{field_label}" segreta'))
def paid_adapter(keys: SourceKeys, adapter: str, field_label: str) -> None:
    keys.paid = offer_paid_sentiment(keys.cycles, adapter)
    assert (API_KEY.label.casefold(), API_KEY.secret) == (field_label.casefold(), True)


@given(quoted('che l\'adapter "{adapter}" non è configurato'))
def not_configured(keys: SourceKeys, adapter: str) -> None:
    assert not keys.summary("anna", adapter).configured


@given(quoted('che il flusso "{flow}" usa l\'adapter "{adapter}"'))
def flow_uses_adapter(keys: SourceKeys, flow: str, adapter: str) -> None:
    configure_paid(keys.cycles, "anna", adapter, TYPED_KEY)
    use_paid_sentiment(keys.cycles, flow, adapter)
    tenant_id = keys.cycles.platform.tenant_of("anna")
    keys.cycles.platform.chats[tenant_id] = LinkedChat(tenant_id, chat_named("anna"))


@given(quoted('che "{user}" ha configurato l\'adapter "{adapter}"'))
def other_user_configured(keys: SourceKeys, user: str, adapter: str) -> None:
    configure_paid(keys.cycles, user, adapter)
    assert keys.summary(user, adapter).configured


# When


@when(quoted('"{user}" inserisce la chiave API dell\'adapter "{adapter}"'))
def enters_key(keys: SourceKeys, user: str, adapter: str) -> None:
    configure_paid(keys.cycles, user, adapter, TYPED_KEY)


@when(quoted('"{user}" prova ad attivarlo nel flusso "{flow}"'))
def tries_to_activate(keys: SourceKeys, user: str, flow: str) -> None:
    request = SourceRequest(SENTIMENT, (AdapterRequest(keys.adapter().name, None),))
    modify(keys.cycles.platform, keys.lifecycle, user, flow, sources=(request,))


@when(quoted('"{user}" apre la sezione "Fonti" delle chiavi'))
def opens_sources_section(keys: SourceKeys, user: str) -> None:
    keys.seen = keys.section(user)


@when("nel ciclo il fornitore rifiuta la chiave")
def provider_refuses(keys: SourceKeys) -> None:
    keys.adapter().rejects_credentials = True
    keys.cycles.run("alfa")


# Then


@then(quoted('l\'adapter "{adapter}" risulta configurato'))
def configured(keys: SourceKeys, adapter: str) -> None:
    summary = keys.summary("anna", adapter)
    assert summary.configured
    assert summary.registered_at is not None


@then("la chiave non è mostrata in chiaro")
def key_not_shown(keys: SourceKeys) -> None:
    [summary] = keys.section("anna")
    answered = SourceCredentialsResponse.of(summary).model_dump_json()
    assert TYPED_KEY not in answered
    assert TYPED_KEY not in repr(summary)
    [credentials] = keys.cycles.platform.source_credentials.credentials
    assert TYPED_KEY.encode() not in credentials.sealed.ciphertext
    assert dict(credentials.public_values) == {}


@then(quoted('l\'attivazione è rifiutata con il motivo "{reason}"'))
def activation_refused(keys: SourceKeys, reason: str) -> None:
    assert str(keys.lifecycle.error) == reason
    # It stays in the list of the flow, with the reason it cannot be activated.
    offers = keys.cycles.platform.use_cases_of("anna").list_source_offers.execute()
    [offer] = [each for each in offers if each.source.name == SENTIMENT]
    [declared] = [each for each in offer.source.adapters if each.name == keys.adapter().name]
    assert (offer.configured(declared), offer.missing_configuration(declared)) == (False, reason)


@then(quoted('l\'adapter "{adapter}" non è elencato tra quelli da configurare'))
def not_listed(keys: SourceKeys, adapter: str) -> None:
    listed = [summary.adapter for summary in keys.seen]
    assert adapter not in listed
    assert listed == [keys.adapter().name]


@then(quoted('l\'adapter "{adapter}" è assente nel contesto del ciclo con il motivo'))
def absent_in_cycle(keys: SourceKeys, adapter: str) -> None:
    [absent] = keys.cycles.last_record("alfa").absent_sources
    assert (absent.source, absent.adapter, absent.reason) == (
        SENTIMENT,
        adapter,
        f"credenziali rifiutate dal fornitore: {adapter}",
    )
    assert keys.adapter().received[-1] == {API_KEY.name: TYPED_KEY}
    assert keys.summary("anna", adapter).rejected


@then(quoted('"{user}" riceve un avviso'))
def receives_notice(keys: SourceKeys, user: str) -> None:
    platform = keys.cycles.platform
    heading = f"adapter {keys.adapter().name}: credenziali rifiutate dal fornitore"
    told = [text for text in platform.messenger.received_by(chat_named(user)) if heading in text.splitlines()[0]]
    assert len(told) == 1
    assert "Cosa fare: sostituiscile in Impostazioni \u203a Chiavi" in told[0].splitlines()
    page = platform.use_cases_of(user).list_inbox_notifications.execute(ListInboxNotificationsCommand())
    assert [notification.title for notification in page.notifications].count(heading) == 1
    # Told once: the next cycle refused again stays silent until the user replaces the key.
    keys.cycles.run("alfa", "10:15")
    assert len(platform.messenger.received_by(chat_named(user))) == 1


@then(quoted('l\'adapter "{adapter}" risulta non configurato per "{user}"'))
def not_configured_for(keys: SourceKeys, adapter: str, user: str) -> None:
    [summary] = [each for each in keys.seen if each.adapter == adapter]
    assert not summary.configured
    assert summary.public_values == {}
    assert user == "anna"
