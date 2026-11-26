import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.agent.agent_context import (
    AgentContext,
    FlowStateView,
    MessageRole,
    PositionView,
    SourceData,
    elapsed_text,
)
from autotrading.domain.agent.decision import TradeDirection
from autotrading.domain.agent.errors import InvalidAgentContextError
from autotrading.domain.agent.exit_plan import ExitPlan

STARTED = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)
LONG_BTC = PositionView(
    "BTC", TradeDirection.LONG, Decimal("0.01"), 3, Decimal(60000), Decimal(61250), Decimal("12.5"), Decimal(41000)
)
STATE = FlowStateView("USDC", Decimal(400), Decimal(380), Decimal(250), Decimal(412), Decimal("2.5"), (LONG_BTC,))
RSI = SourceData("indicatori", "Hyperliquid", 7, "BTC", {"rsi_14": "61.2"})
FEAR = SourceData("sentiment", "alternative.me", 3, None, {"valore": "29", "classificazione": "Fear"})


def context(**changes: object) -> AgentContext:
    values: dict[str, object] = {
        "system_prompt": "Sei un trader prudente su BTC, ETH",
        "assets": ("BTC", "ETH"),
        "started_at": STARTED,
        "now": NOW,
        "state": STATE,
        "sources": (RSI, FEAR),
        "missing": ("forecast: servizio non raggiungibile",),
    }
    values.update(changes)
    return AgentContext(**values)  # type: ignore[arg-type]  # the keyword values of the test, checked by the type


def system_text(agent_context: AgentContext) -> str:
    system, _ = agent_context.messages()
    assert system.role is MessageRole.SYSTEM
    return system.content


def user_document(agent_context: AgentContext) -> dict[str, object]:
    _, user = agent_context.messages()
    assert user.role is MessageRole.USER
    document: dict[str, object] = json.loads(user.content)
    return document


def test_the_system_message_is_the_system_prompt_the_flow_rendered() -> None:
    assert system_text(context()) == "Sei un trader prudente su BTC, ETH"


def test_the_user_message_has_the_time_and_the_time_since_the_start() -> None:
    document = user_document(context())

    assert document["ora_corrente"] == "2026-11-12T10:30+00:00"
    assert document["tempo_dall_avvio"] == "2 ore e 30 minuti"


def test_the_user_message_has_the_state_of_the_flow() -> None:
    assert user_document(context())["stato_del_flusso"] == {
        "valuta": "USDC",
        "capitale_allocato": "400",
        "soldi_del_flusso": "380",
        "liquidita_disponibile": "250",
        "valore_complessivo": "412",
        "rendimento_dall_avvio_percento": "2.5",
        "posizioni_aperte": [
            {
                "asset": "BTC",
                "direzione": "long",
                "dimensione": "0.01",
                "leva": 3,
                "prezzo_di_ingresso": "60000",
                "prezzo_di_mercato": "61250",
                "pnl_non_realizzato": "12.5",
                "prezzo_di_liquidazione": "41000",
                "obiettivo": None,
                "stop": None,
                "invalidazione": None,
            }
        ],
    }


def test_a_position_carries_the_exit_plan_in_force() -> None:
    plan = ExitPlan(Decimal(63000), Decimal("58500.5"), "chiusura a 4 ore sotto 59000")
    planned = replace(LONG_BTC, exit_plan=plan)
    state = replace(STATE, positions=(planned,))

    document = user_document(context(state=state))["stato_del_flusso"]

    assert isinstance(document, dict)
    [position] = document["posizioni_aperte"]
    assert (position["obiettivo"], position["stop"], position["invalidazione"]) == (
        "63000",
        "58500.5",
        "chiusura a 4 ore sotto 59000",
    )


def test_a_return_that_cannot_be_measured_is_null() -> None:
    state = FlowStateView("USDC", Decimal(0), Decimal(0), Decimal(0), Decimal(0), None, ())

    flow_state = user_document(context(state=state))["stato_del_flusso"]

    assert isinstance(flow_state, dict)
    assert flow_state["rendimento_dall_avvio_percento"] is None


def test_a_position_without_liquidation_price_says_so() -> None:
    cross = PositionView("ETH", TradeDirection.SHORT, Decimal(1), 1, Decimal(3000), Decimal(3000), Decimal(0), None)
    state = FlowStateView("USDC", Decimal(400), Decimal(400), Decimal(250), Decimal(400), Decimal(0), (cross,))

    position = user_document(context(state=state))["stato_del_flusso"]

    assert isinstance(position, dict)
    assert position["posizioni_aperte"][0]["prezzo_di_liquidazione"] is None


def test_the_user_message_has_the_sources_with_their_weights_and_the_missing_data() -> None:
    document = user_document(context())

    assert document["fonti"] == [
        {"fonte": "indicatori", "adapter": "Hyperliquid", "peso": 7, "asset": "BTC", "valori": {"rsi_14": "61.2"}},
        {
            "fonte": "sentiment",
            "adapter": "alternative.me",
            "peso": 3,
            "asset": None,
            "valori": {"valore": "29", "classificazione": "Fear"},
        },
    ]
    assert document["dati_mancanti"] == ["forecast: servizio non raggiungibile"]


def test_an_aggregate_of_several_adapters_carries_no_weight_of_its_own() -> None:
    aggregate = SourceData("volumi", "aggregato", None, "BTC", {"volume_24h_usd": "400"})

    document = user_document(context(sources=(RSI, aggregate)))

    assert document["fonti"] == [
        {"fonte": "indicatori", "adapter": "Hyperliquid", "peso": 7, "asset": "BTC", "valori": {"rsi_14": "61.2"}},
        {"fonte": "volumi", "adapter": "aggregato", "asset": "BTC", "valori": {"volume_24h_usd": "400"}},
    ]


def test_the_context_has_nothing_but_what_it_declares() -> None:
    assert set(user_document(context())) == {
        "ora_corrente",
        "tempo_dall_avvio",
        "stato_del_flusso",
        "fonti",
        "dati_mancanti",
    }


def test_accented_text_is_kept_as_written() -> None:
    _, user = context(missing=("notizie: nessuna notizia nell'ultima ora, città",)).messages()

    assert "città" in user.content


@pytest.mark.parametrize(
    ("started_at", "now"),
    [
        (datetime(2026, 11, 12, 8, 0), NOW),
        (STARTED, datetime(2026, 11, 12, 10, 30)),
        (NOW, STARTED),
    ],
)
def test_times_without_zone_or_in_the_wrong_order_are_a_defect(started_at: datetime, now: datetime) -> None:
    with pytest.raises(InvalidAgentContextError, match=r"^contesto dell'agente non valido$"):
        context(started_at=started_at, now=now)


@pytest.mark.parametrize(
    ("elapsed", "text"),
    [
        (timedelta(0), "0 minuti"),
        (timedelta(seconds=59), "0 minuti"),
        (timedelta(minutes=1), "1 minuto"),
        (timedelta(minutes=45), "45 minuti"),
        (timedelta(hours=1), "1 ora"),
        (timedelta(hours=2, minutes=30), "2 ore e 30 minuti"),
        (timedelta(days=1), "1 giorno"),
        (timedelta(days=3, minutes=5), "3 giorni e 5 minuti"),
        (timedelta(days=2, hours=1, minutes=1), "2 giorni, 1 ora e 1 minuto"),
    ],
)
def test_the_time_since_the_start_is_spoken(elapsed: timedelta, text: str) -> None:
    assert elapsed_text(elapsed) == text


def test_the_first_cycle_runs_at_the_start() -> None:
    assert user_document(context(now=STARTED))["tempo_dall_avvio"] == "0 minuti"


def test_a_position_carries_the_largest_profit_it_reached_only_when_the_flow_gives_it() -> None:
    # R5.5.1, ADR massimo-profitto-raggiunto-nello-stato-della-posizione: without it the state is the one of before.
    state = replace(STATE, positions=(replace(LONG_BTC, max_profit=Decimal("30.5")), LONG_BTC))

    document = user_document(context(state=state))["stato_del_flusso"]

    assert isinstance(document, dict)
    reached, plain = document["posizioni_aperte"]
    assert reached["massimo_profitto_raggiunto"] == "30.5"
    assert "massimo_profitto_raggiunto" not in plain
