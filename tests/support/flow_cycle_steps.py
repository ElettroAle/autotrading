"""The steps of the scenarios that run a cycle of a real flow on the bridges of the worker (ADR 0042).

A scenario module imports them all; pytest-bdd keeps each step as a fixture of this module.
"""

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.agent.errors import ModelCreditExhaustedError, ModelKeyRejectedError
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.cycles.cycle_record import CycleOutcome
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.sources.sentiment_index import SentimentIndex
from tests.support.activity import a_position, an_activity
from tests.support.flow_cycles import BALANCE, FlowCycles, at
from tests.support.flows import ANTHROPIC_MODEL
from tests.support.steps import quoted


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


def names_of(text: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in text.split(","))


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def position(asset: str, side: PositionSide = PositionSide.LONG, **values: object) -> Position:
    fields: dict[str, object] = {
        "coin": asset,
        "side": side,
        "size": Decimal("0.01"),
        "leverage": 1,
        "entry_price": Decimal(100),
        "unrealized_pnl": Decimal(0),
        "liquidation_price": None,
    }
    fields.update(values)
    return Position(**fields)  # type: ignore[arg-type]  # the keyword values of the test, checked by the type


# Given: the flows


@given(
    quoted(
        'che "{user}" ha i flussi "{first}" e "{second}" attivi sul conto "{account}" '
        'con modelli del fornitore "{provider}"'
    )
)
def two_flows_on_account(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles, user: str, first: str, second: str, account: str, provider: str
) -> None:
    model = ANTHROPIC_MODEL if provider == "anthropic" else f"{provider}/deepseek-chat"
    for name in (first, second):
        flow_cycles.add_flow(user, name, model=model, account=account)


@given(quoted('che "{user}" ha anche il flusso "{flow}" attivo con un modello del fornitore "{provider}"'))
def flow_of_other_provider(flow_cycles: FlowCycles, user: str, flow: str, provider: str) -> None:
    flow_cycles.add_flow(user, flow, model=ANTHROPIC_MODEL if provider == "anthropic" else f"{provider}/deepseek-chat")


@given(quoted('che "{user}" ha il flusso "{flow}" con asset "{assets}" e la fonte "{source}" attiva'))
def flow_with_source(flow_cycles: FlowCycles, user: str, flow: str, assets: str, source: str) -> None:
    flow_cycles.add_flow(user, flow, assets=names_of(assets), sources=(source,))


@given(quoted('che "{user}" ha il flusso "{flow}" con la fonte "{source}" attiva'))
def flow_with_market_source(flow_cycles: FlowCycles, user: str, flow: str, source: str) -> None:
    flow_cycles.add_flow(user, flow, sources=(source,))


@given(quoted('che "{user}" ha il flusso "{flow}" con le fonti "{sources}" attive'))
def flow_with_sources(flow_cycles: FlowCycles, user: str, flow: str, sources: str) -> None:
    flow_cycles.add_flow(user, flow, sources=names_of(sources))


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "(?P<flow>[^"]+)" avviato alle (?P<started>\d\d:\d\d) con asset '
        r'"(?P<assets>[^"]+)", leva massima (?P<leverage>\d+) e istruzioni "(?P<instructions>[^"]+)"$'
    )
)
def started_flow(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles, user: str, flow: str, started: str, assets: str, leverage: str, instructions: str
) -> None:
    flow_cycles.add_flow(user, flow, assets=names_of(assets), started=started)
    flow_cycles.reconfigure(
        flow,
        lambda configuration: replace(
            configuration, instructions=instructions, risk_limits=RiskLimits(int(leverage), Decimal(10))
        ),
    )


@given(quoted('che il flusso "{flow}" è stato messo in pausa e ripreso alle {clock}'))
def paused_and_resumed(flow_cycles: FlowCycles, flow: str, clock: str) -> None:
    # As the trigger of the database: a resume moves the anchor of the cycles, never the first start.
    flow_cycles.platform.flows.anchors[flow_cycles.flow(flow).id] = at(clock)


@given(quoted('che "{user}" ha anche il flusso "{flow}" sullo stesso conto con asset "{assets}"'))
def other_flow_same_account(flow_cycles: FlowCycles, user: str, flow: str, assets: str) -> None:
    flow_cycles.add_flow(user, flow, assets=names_of(assets))


# Given: the account and the exchange


@given(quoted('che il flusso "{flow}" ha una posizione aperta su "{asset}"'))
def open_position(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    flow_cycles.platform.hyperliquid.open_position(flow_cycles.credentials_of(flow), position(asset))


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha capitale allocato (?P<capital>[\d,]+) USDC, liquidità disponibile '
        r'(?P<liquidity>[\d,]+) USDC e una posizione long su "(?P<asset>[^"]+)" con leva (?P<leverage>\d+)$'
    )
)
def flow_state(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles, flow: str, capital: str, liquidity: str, asset: str, leverage: str
) -> None:
    allocated = number(capital)
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, allocated_capital=allocated))
    # The margin of the position is what the capital lacks to reach the liquidity: value / leverage.
    margin = allocated - number(liquidity)
    entry_price = Decimal(30000)
    size = margin * int(leverage) / entry_price
    held = position(
        asset,
        size=size,
        leverage=int(leverage),
        entry_price=entry_price,
        liquidation_price=Decimal(20000),
    )
    flow_cycles.platform.hyperliquid.open_position(flow_cycles.credentials_of(flow), held)
    show_activity(flow_cycles, flow, a_position(asset, margin=margin))


def show_activity(flow_cycles: FlowCycles, flow: str, held: AccountPosition) -> None:
    """The same position as the activity of the account shows it: the state of the flow is attributed from it."""
    address = flow_cycles.credentials_of(flow).account_address
    flow_cycles.platform.activity_reader.activities[address] = an_activity(positions=(held,))


@given(parsers.re(r'^che il flusso "(?P<flow>[^"]+)" ha un rendimento dall\'avvio del (?P<percent>[\d,]+)%$'))
def flow_return(flow_cycles: FlowCycles, flow: str, percent: str) -> None:
    credentials = flow_cycles.credentials_of(flow)
    exchange = flow_cycles.platform.hyperliquid
    state = exchange.read_state(credentials)
    [held] = [held for held in state.positions if held.coin in flow_cycles.flow(flow).configuration.assets]
    pnl = flow_cycles.flow(flow).configuration.allocated_capital * number(percent) / 100
    exchange.revoke(credentials)
    exchange.accept(credentials, amount=BALANCE)
    exchange.open_position(credentials, replace(held, unrealized_pnl=pnl))
    [shown] = flow_cycles.platform.activity_reader.activities[credentials.account_address].positions
    show_activity(flow_cycles, flow, replace(shown, unrealized_pnl=pnl))


@given(quoted('che l\'exchange rifiuta le credenziali del conto "{account}"'))
def credentials_rejected(flow_cycles: FlowCycles, account: str) -> None:
    tenant_id = next(iter(flow_cycles.credentials))[0]
    flow_cycles.platform.hyperliquid.revoke(flow_cycles.credentials[tenant_id, account])


# Given: the provider of the model


@given(quoted('che il fornitore "{provider}" risponde credito esaurito'))
def credit_exhausted(flow_cycles: FlowCycles, provider: str) -> None:
    flow_cycles.model.failure = ModelCreditExhaustedError(ProviderName(provider))


@given(quoted('che il fornitore "{provider}" rifiuta la chiave'))
def key_rejected(flow_cycles: FlowCycles, provider: str) -> None:
    flow_cycles.model.failure = ModelKeyRejectedError(ProviderName(provider))


# Given: the sources


@given(quoted('che l\'ultimo prezzo di "{asset}" è {price}'))
def last_price(flow_cycles: FlowCycles, asset: str, price: str) -> None:
    flow_cycles.prices.prices[asset] = number(price)


@given(quoted('che il flusso "{flow}" ha la profondità dello storico del forecast a {days} giorni'))
def forecast_depth(flow_cycles: FlowCycles, flow: str, days: str) -> None:
    flow_cycles.set_source_parameters(flow, "forecast", profondita_storico_giorni=int(days))


@given(quoted('che per "{asset}" sono disponibili solo {days} giorni di storico'))
def short_history(flow_cycles: FlowCycles, asset: str, days: str) -> None:  # noqa: ARG001 - one asset in the flow
    flow_cycles.prices.available_days = int(days)


@given(quoted('che l\'indice Fear & Greed di "{source}" vale {value} con classificazione "{classification}"'))
def sentiment_index(flow_cycles: FlowCycles, source: str, value: str, classification: str) -> None:
    flow_cycles.sentiments[source].index = SentimentIndex(int(value), classification, at("06:00"))


@given(
    parsers.re(
        r"^che sono disponibili (?P<total>\d+) notizie pubblicate nelle ultime (?P<hours>\d+) ore, "
        r"(?P<recent>\d+) delle quali nelle ultime (?P<recent_hours>\d+) ore$"
    )
)
def available_news(flow_cycles: FlowCycles, total: str, hours: str, recent: str, recent_hours: str) -> None:
    now = flow_cycles.clock.now()
    recent_count, older_count = int(recent), int(total) - int(recent)
    recent_span, whole_span = timedelta(hours=int(recent_hours)), timedelta(hours=int(hours))
    # The recent stories start after the first hour and stay within their span; the others fill the rest.
    recent_ages = [
        timedelta(hours=1) + (recent_span - timedelta(hours=2)) * index / recent_count
        for index in range(1, recent_count + 1)
    ]
    older_ages = [
        recent_span + (whole_span - recent_span) * index / (older_count + 1) for index in range(1, older_count + 1)
    ]
    flow_cycles.news.stories = [
        NewsItem(f"notizia {index}", now - age, f"sintesi {index}")
        for index, age in enumerate(sorted(recent_ages + older_ages))
    ]


@given(
    parsers.re(r'^che il flusso "(?P<flow>[^"]+)" ha numero notizie (?P<count>\d+) ed età massima (?P<hours>\d+) ore$')
)
def news_parameters(flow_cycles: FlowCycles, flow: str, count: str, hours: str) -> None:
    flow_cycles.set_source_parameters(flow, "notizie", numero_notizie=int(count), eta_massima_ore=int(hours))


@given(parsers.re(r'^che il flusso "(?P<flow>[^"]+)" ha età massima 1 ora$'))
def news_last_hour(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.set_source_parameters(flow, "notizie", eta_massima_ore=1)


@given("che nessuna notizia è stata pubblicata nell'ultima ora")
def no_news_last_hour(flow_cycles: FlowCycles) -> None:
    now = flow_cycles.clock.now()
    assert all(story.published_at < now - timedelta(hours=1) for story in flow_cycles.news.stories)


# When


@when(quoted('il flusso "{flow}" esegue un ciclo'))
def run_cycle(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.run(flow)


@when(parsers.re(r'^il flusso "(?P<flow>[^"]+)" esegue un ciclo alle (?P<clock>\d\d:\d\d)$'))
def run_cycle_at(flow_cycles: FlowCycles, flow: str, clock: str) -> None:
    flow_cycles.run(flow, clock)


# Then: the cycle and the flows


@then(quoted('il ciclo è registrato come fallito con il motivo "{reason}"'))
def cycle_failed(flow_cycles: FlowCycles, reason: str) -> None:
    record = flow_cycles.last_record("alfa")
    assert record.outcome is CycleOutcome.FAILED
    assert record.failure is not None
    assert record.failure.message == reason


@then(quoted('il flusso "{flow}" è nello stato "{status}" con il motivo "{reason}"'))
def flow_paused_with_reason(flow_cycles: FlowCycles, flow: str, status: str, reason: str) -> None:
    paused = flow_cycles.flow(flow)
    assert paused.status.value == status
    assert flow_cycles.platform.flows.pause_reasons[paused.id] == reason


@then(quoted('il flusso "{flow}" è nello stato "{status}"'))
def flow_in_status(flow_cycles: FlowCycles, flow: str, status: str) -> None:
    assert flow_cycles.flow(flow).status.value == status


@then(quoted('la posizione su "{asset}" resta aperta sull\'exchange'))
def position_still_open(flow_cycles: FlowCycles, asset: str) -> None:
    state = flow_cycles.platform.hyperliquid.read_state(flow_cycles.credentials_of("alfa"))
    assert asset in {held.coin for held in state.positions}
    assert flow_cycles.platform.order_exchange.sent == []


# Then: the forecast


@then(quoted('il contesto contiene per "{asset}" una previsione a 15 minuti e una a 1 ora'))
def forecasts_in_context(flow_cycles: FlowCycles, asset: str) -> None:
    [values] = flow_cycles.sources_in_context("forecast", asset)
    for horizon in ForecastHorizon:
        assert f"prezzo_previsto_{horizon.label}" in values


@then(
    quoted(
        "ogni previsione riporta ultimo prezzo {price}, prezzo previsto, variazione percentuale prevista e orizzonte"
    )
)
def forecast_values(flow_cycles: FlowCycles, price: str) -> None:
    for values in flow_cycles.sources_in_context("forecast"):
        assert number(values["prezzo_attuale"]) == number(price)
        for horizon in ForecastHorizon:
            assert Decimal(values[f"prezzo_previsto_{horizon.label}"]) > 0
            Decimal(values[f"variazione_percentuale_{horizon.label}"])


@then(quoted('la previsione per "{asset}" usa {days} giorni di storico'))
def forecast_depth_used(flow_cycles: FlowCycles, asset: str, days: str) -> None:
    [values] = flow_cycles.sources_in_context("forecast", asset)
    assert values["profondita_storico_giorni"] == days


@then(quoted('il contesto dichiara per "{asset}" lo storico ridotto a {days} giorni'))
def shortened_history(flow_cycles: FlowCycles, asset: str, days: str) -> None:
    [values] = flow_cycles.sources_in_context("forecast", asset)
    assert values["profondita_storico_giorni"] == days
    assert "storico_ridotto" in values


@given(quoted('che alle {clock} il flusso "{flow}" ha registrato per "{asset}" una previsione a 15 minuti di {price}'))
def recorded_forecast(flow_cycles: FlowCycles, clock: str, flow: str, asset: str, price: str) -> None:
    recorded = flow_cycles.flow(flow)
    forecast = PriceForecast(
        recorded.id.value, asset, ForecastHorizon.MINUTES_15, at(clock), Decimal(100), number(price), 7, False
    )
    flow_cycles.forecasts_of(recorded.tenant_id).add(forecast)


@when(quoted('arrivano le {clock} e il prezzo di "{asset}" è {price}'))
def horizon_expires(flow_cycles: FlowCycles, clock: str, asset: str, price: str) -> None:
    flow_cycles.prices.prices[asset] = number(price)
    flow_cycles.clock.current = at(clock)
    flow_cycles.plan_round()


@then(quoted('la previsione delle {clock} per "{asset}" a 15 minuti ha registrato il prezzo effettivo {price}'))
def actual_price_recorded(flow_cycles: FlowCycles, clock: str, asset: str, price: str) -> None:
    tenant_id = flow_cycles.flow("alfa").tenant_id
    recorded = [
        forecast.actual_price
        for forecast in flow_cycles.forecasts_of(tenant_id).forecasts
        if (forecast.made_at, forecast.asset, forecast.horizon.minutes) == (at(clock), asset, 15)
    ]
    assert recorded == [number(price)]


# Then: the sentiment


@then(
    quoted(
        'il contesto contiene una sola volta l\'indice Fear & Greed di "{source}" con valore {value} '
        'e classificazione "{classification}"'
    )
)
def sentiment_once(flow_cycles: FlowCycles, source: str, value: str, classification: str) -> None:
    [values] = flow_cycles.sources_in_context(source)
    assert (values["valore"], values["classificazione"]) == (value, classification)


@then(quoted("il contesto riporta l'istante di aggiornamento dell'indice di \"{source}\""))
def sentiment_updated_at(flow_cycles: FlowCycles, source: str) -> None:
    [values] = flow_cycles.sources_in_context(source)
    assert datetime.fromisoformat(values["aggiornato_alle"]) == at("06:00")


@then(
    quoted(
        'il contesto contiene l\'indice di "{first}" con valore {first_value} e quello di "{second}" con valore '
        "{second_value}, ciascuno con la propria fonte"
    )
)
def both_sentiments(flow_cycles: FlowCycles, first: str, first_value: str, second: str, second_value: str) -> None:
    [first_values] = flow_cycles.sources_in_context(first)
    [second_values] = flow_cycles.sources_in_context(second)
    assert (first_values["valore"], second_values["valore"]) == (first_value, second_value)


# Then: the news


def news_in_context(flow_cycles: FlowCycles) -> list[dict[str, str]]:
    return flow_cycles.sources_in_context("notizie")


@then(quoted("il contesto contiene {count} notizie pubblicate nelle ultime {hours} ore"))
def news_within(flow_cycles: FlowCycles, count: str, hours: str) -> None:
    news = news_in_context(flow_cycles)
    oldest_allowed = flow_cycles.clock.now() - timedelta(hours=int(hours))
    assert len(news) == int(count)
    assert all(datetime.fromisoformat(values["pubblicata_alle"]) >= oldest_allowed for values in news)


@then("ogni notizia riporta titolo, data e ora di pubblicazione e sintesi")
def news_fields(flow_cycles: FlowCycles) -> None:
    for values in news_in_context(flow_cycles):
        assert values["titolo"]
        assert values["sintesi"]
        datetime.fromisoformat(values["pubblicata_alle"])


@then("le notizie sono ordinate dalla più recente")
def news_newest_first(flow_cycles: FlowCycles) -> None:
    published = [datetime.fromisoformat(values["pubblicata_alle"]) for values in news_in_context(flow_cycles)]
    assert published == sorted(published, reverse=True)


@then(quoted("il contesto contiene {count} notizie"))
def news_count(flow_cycles: FlowCycles, count: str) -> None:
    assert len(news_in_context(flow_cycles)) == int(count)


@then("il contesto dichiara che non ci sono notizie nell'ultima ora")
def no_news_declared(flow_cycles: FlowCycles) -> None:
    assert news_in_context(flow_cycles) == [{"nota": "nessuna notizia nell'ultima ora"}]


# Then: the context of the agent


@then(quoted('il contesto contiene le istruzioni "{instructions}"'))
def instructions_in_context(flow_cycles: FlowCycles, instructions: str) -> None:
    assert flow_cycles.system_text().startswith(instructions + "\n")


@then(quoted("il contesto contiene le regole operative con leva ammessa da {lowest} a {highest}"))
def operational_rules(flow_cycles: FlowCycles, lowest: str, highest: str) -> None:
    text = flow_cycles.system_text()
    assert f"- leva da {lowest} a {highest};" in text
    assert "- al massimo una posizione per asset;" in text
    assert "- azioni ammesse: apri, chiudi, mantieni;" in text
    assert '{"decisioni": [' in text


@then(
    parsers.re(
        r"^il contesto contiene l'ora corrente (?P<clock>\d\d:\d\d) e il tempo trascorso dall'avvio di "
        r"(?P<elapsed>.+)$"
    )
)
def time_in_context(flow_cycles: FlowCycles, clock: str, elapsed: str) -> None:
    context = flow_cycles.context()
    assert context["ora_corrente"] == at(clock).isoformat(timespec="minutes")
    assert context["tempo_dall_avvio"] == elapsed


def state_in_context(flow_cycles: FlowCycles) -> dict[str, object]:
    state = flow_cycles.context()["stato_del_flusso"]
    assert isinstance(state, dict)
    return state


@then(
    parsers.re(
        r"^il contesto contiene capitale allocato (?P<capital>[\d,]+) USDC e liquidità disponibile "
        r"(?P<liquidity>[\d,]+) USDC$"
    )
)
def capital_in_context(flow_cycles: FlowCycles, capital: str, liquidity: str) -> None:
    state = state_in_context(flow_cycles)
    assert state["valuta"] == "USDC"
    assert Decimal(str(state["capitale_allocato"])) == number(capital)
    assert Decimal(str(state["liquidita_disponibile"])) == number(liquidity)


@then(parsers.re(r"^il contesto contiene il rendimento dall'avvio del (?P<percent>[\d,]+)%$"))
def return_in_context(flow_cycles: FlowCycles, percent: str) -> None:
    assert Decimal(str(state_in_context(flow_cycles)["rendimento_dall_avvio_percento"])) == number(percent)


@then(
    parsers.re(
        r'^il contesto contiene la posizione long su "(?P<asset>[^"]+)" con dimensione, leva (?P<leverage>\d+), '
        r"prezzo di ingresso, PnL non realizzato e prezzo di liquidazione$"
    )
)
def position_in_context(flow_cycles: FlowCycles, asset: str, leverage: str) -> None:
    positions = state_in_context(flow_cycles)["posizioni_aperte"]
    assert isinstance(positions, list)
    [held] = [held for held in positions if held["asset"] == asset]
    assert (held["direzione"], held["leva"]) == ("long", int(leverage))
    for field in ("dimensione", "prezzo_di_ingresso", "pnl_non_realizzato", "prezzo_di_liquidazione"):
        Decimal(held[field])


@then(quoted('il contesto non contiene la posizione su "{asset}"'))
def position_not_in_context(flow_cycles: FlowCycles, asset: str) -> None:
    positions = state_in_context(flow_cycles)["posizioni_aperte"]
    assert isinstance(positions, list)
    assert asset not in {held["asset"] for held in positions}
    assert f'"{asset}"' not in str(flow_cycles.model.calls[-1].messages[1].content)


@then("il contesto non contiene il saldo del conto")
def balance_not_in_context(flow_cycles: FlowCycles) -> None:
    for message in flow_cycles.model.calls[-1].messages:
        assert str(BALANCE) not in message.content
        assert "saldo" not in message.content
