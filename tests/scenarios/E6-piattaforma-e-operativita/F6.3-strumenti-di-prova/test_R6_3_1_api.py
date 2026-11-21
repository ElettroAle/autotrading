"""R6.3.1: the trial of a source, from the use case of the API through the worker, which reads the adapter as a cycle
does and records nothing (ADR prova-di-un-adapter-di-fonte-nel-worker). playwright-bdd runs the same scenarios on the
build of the dashboard (ADR pagina-fonti-con-la-prova); here being on the page is reading the catalog it lists, and a
trial without an asset named takes the first asset the exchange trades, as the page proposes it.
"""

from dataclasses import dataclass, field, replace
from datetime import timedelta

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.sources.configure_source_adapter import ConfigureSourceAdapterCommand
from autotrading.application.sources.request_source_trial import RequestSourceTrialCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.sources.source_trial import SourceTrial, TrialOutcome
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter
from tests.support.flows import a_configuration, a_flow
from tests.support.platform import Platform
from tests.support.source_keys import API_KEY
from tests.support.source_selections import a_source, adapter_of
from tests.support.steps import quoted

scenarios(
    "E6-piattaforma-e-operativita/F6.3-strumenti-di-prova/R6.3.1-prova-delle-fonti/api/R6.3.1-prova-delle-fonti.feature"
)

OUTCOMES = {"riuscita": TrialOutcome.SUCCEEDED, "errore": TrialOutcome.FAILED}
PERMANENCE = {"transitorio": False, "permanente": True}
# Beyond the series length every adapter of the indicators admits (R1.3.3).
OUT_OF_RANGE = 51
KEY_OF_ANNA = "K-LUNAR-ANNA"


@dataclass
class Page:
    """The page Fonti of a user: the sources it lists and the last trial, or the refusal that stopped it."""

    user: str = ""
    sources: tuple[str, ...] = ()
    trial: SourceTrial | None = None
    refusal: AutotradingError | None = None
    flows: dict[str, Flow] = field(default_factory=dict)
    paid: FakeSentimentAdapter | None = None

    @property
    def tried(self) -> SourceTrial:
        assert self.trial is not None, f"nessuna prova eseguita: {self.refusal}"
        return self.trial

    @property
    def refused(self) -> AutotradingError:
        assert self.refusal is not None, "la prova non è stata rifiutata"
        return self.refusal


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    # Time passes while the worker reads the source: the trial measures it (R6.3.1).
    platform.worker_clock.step = timedelta(milliseconds=180)
    return platform


@pytest.fixture
def page() -> Page:
    return Page()


def try_source(platform: Platform, page: Page, source: str, asset: str | None = None, **parameters: int) -> None:
    use_cases = platform.use_cases_of(page.user)
    per_asset = next(
        offer.source.per_asset for offer in use_cases.list_source_offers.execute() if offer.source.name == source
    )
    # The page proposes the first asset the exchange trades for a per-asset source.
    chosen = asset if asset is not None or not per_asset else sorted(use_cases.list_tradable_assets.execute())[0]
    command = RequestSourceTrialCommand(source, adapter_of(source), chosen, parameters)
    try:
        page.trial = use_cases.request_source_trial.execute(command)
    except AutotradingError as error:
        page.refusal = error


@given(quoted('che "{user}" è nella pagina Fonti della dashboard'))
def on_the_sources_page(platform: Platform, page: Page, user: str) -> None:
    page.user = user
    page.sources = tuple(offer.source.name for offer in platform.use_cases_of(user).list_source_offers.execute())
    assert page.sources


@given(quoted('che la fonte "{source}" non risponde'))
def source_not_answering(platform: Platform, source: str) -> None:
    assert source == "notizie"
    platform.source_systems = replace(platform.source_systems, news=FakeNewsAdapter(reachable=False))


@given(quoted('che "{user}" ha il flusso "{name}" con la fonte "{source}"'))
def flow_with_source(platform: Platform, page: Page, user: str, name: str, source: str) -> None:
    configuration = replace(a_configuration(), sources=(a_source(source),))
    flow = a_flow(platform.tenant_of(user), name=name, status=FlowStatus.ACTIVE, configuration=configuration)
    platform.flows.flows.append(flow)
    page.flows[name] = flow


@given(quoted('che "{user}" ha configurato la chiave dell\'adapter "{adapter}" della fonte "{source}"'))
def paid_adapter_configured(platform: Platform, page: Page, user: str, adapter: str, source: str) -> None:
    page.paid = FakeSentimentAdapter(adapter, configuration_fields=(API_KEY,))
    systems = platform.source_systems
    platform.source_systems = replace(systems, sentiments=(*systems.sentiments, page.paid))
    command = ConfigureSourceAdapterCommand(adapter, {API_KEY.name: KEY_OF_ANNA})
    platform.use_cases_of(user).configure_source_adapter.execute(command)
    assert source == "sentiment"


@given(quoted('che il fornitore di "{adapter}" rifiuta la chiave'))
def provider_refuses(page: Page, adapter: str) -> None:
    assert page.paid is not None
    assert page.paid.name == adapter
    page.paid.rejects_credentials = True


@when(quoted('"{user}" prova l\'adapter "{adapter}" della fonte "{source}"'))
def try_adapter(platform: Platform, page: Page, user: str, adapter: str, source: str) -> None:
    command = RequestSourceTrialCommand(source, adapter, None, {})
    try:
        page.trial = platform.use_cases_of(user).request_source_trial.execute(command)
    except AutotradingError as error:
        page.refusal = error


@when(quoted('"{user}" prova la fonte "{source}" per l\'asset "{asset}" con i parametri predefiniti'))
def try_with_defaults(platform: Platform, page: Page, source: str, asset: str) -> None:
    try_source(platform, page, source, asset)


@when(quoted('"{user}" prova la fonte "{source}" con un periodo fuori dai limiti'))
def try_out_of_range(platform: Platform, page: Page, source: str) -> None:
    try_source(platform, page, source, lunghezza_serie=OUT_OF_RANGE)


@when(quoted('"{user}" prova la fonte "{source}"'))
def try_named_source(platform: Platform, page: Page, source: str) -> None:
    try_source(platform, page, source)


@then(quoted("vede l'esito \"{outcome}\", i valori letti, l'istante dei dati e il tempo di risposta"))
def sees_the_values(page: Page, outcome: str) -> None:
    trial = page.tried
    assert trial.outcome is OUTCOMES[outcome]
    assert [value.values["prezzo"] for value in trial.values] == ["100"]
    assert trial.data_at == trial.values[0].reference_at
    assert trial.response_milliseconds == 180


@then(quoted('vede l\'esito "{outcome}" letto con la chiave di "{user}"'))
def sees_reading_with_key(page: Page, outcome: str, user: str) -> None:
    assert page.tried.outcome is OUTCOMES[outcome]
    assert page.tried.values
    assert page.paid is not None
    assert page.paid.received == [{API_KEY.name: KEY_OF_ANNA}]
    assert user == page.user


@then(quoted('vede l\'esito "{outcome}" con il motivo "{reason}" e l\'indicazione "{permanence}"'))
def sees_the_reason(page: Page, outcome: str, reason: str, permanence: str) -> None:
    trial = page.tried
    assert (trial.outcome, trial.reason, trial.permanent) == (OUTCOMES[outcome], reason, PERMANENCE[permanence])


@then(quoted('vede l\'esito "{outcome}" con il motivo e l\'indicazione "{permanence}"'))
def sees_the_failure(page: Page, outcome: str, permanence: str) -> None:
    trial = page.tried
    assert (trial.outcome, trial.reason, trial.permanent) == (
        OUTCOMES[outcome],
        "fonte non raggiungibile: notizie",
        PERMANENCE[permanence],
    )


@then("la prova non parte e il parametro mostra il limite ammesso")
def refused_with_the_limit(platform: Platform, page: Page) -> None:
    market = platform.source_systems.market
    assert isinstance(market, FakeMarketDataAdapter)
    assert (page.trial, market.requests) == (None, [])
    assert (page.refused.status_code, page.refused.details) == (
        422,
        {"field": "lunghezza_serie", "minimum": 1, "maximum": 50},
    )


@then(quoted('i cicli del flusso "{name}" non registrano valori della prova'))
def cycles_untouched(platform: Platform, page: Page, name: str) -> None:
    flow = page.flows[name]
    assert page.tried.outcome is TrialOutcome.SUCCEEDED
    assert [record for record in platform.cycles.records if record.flow_id == flow.id.value] == []
    assert platform.forecasts_of(flow.tenant_id).forecasts == []
    assert platform.flows.flows == [flow]
