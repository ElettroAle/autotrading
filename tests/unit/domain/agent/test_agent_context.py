import json
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

STARTED = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)
LONG_BTC = PositionView("BTC", TradeDirection.LONG, Decimal("0.01"), 3, Decimal(60000), Decimal("12.5"), Decimal(41000))
STATE = FlowStateView("USDC", Decimal(400), Decimal(250), Decimal(412), Decimal("2.5"), (LONG_BTC,))
RSI = SourceData("indicatori", 7, "BTC", {"rsi_14": "61.2"})
FEAR = SourceData("sentiment-alternative-me", 3, None, {"valore": "29", "classificazione": "Fear"})


def context(**changes: object) -> AgentContext:
    values: dict[str, object] = {
        "instructions": "Sei un trader prudente",
        "assets": ("BTC", "ETH"),
        "max_leverage": 5,
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


def test_the_system_message_has_the_instructions_and_the_operational_rules() -> None:
    text = system_text(context())

    assert text.startswith("Sei un trader prudente\n")
    assert "- al massimo una posizione per asset;" in text
    assert "- azioni ammesse: apri, chiudi, mantieni;" in text
    assert "- leva da 1 a 5;" in text
    assert "- una decisione per ciascun asset del flusso: BTC, ETH;" in text
    assert '{"decisioni": [{"asset": "<asset>", "azione": "apri|chiudi|mantieni"' in text


def test_the_user_message_has_the_time_and_the_time_since_the_start() -> None:
    document = user_document(context())

    assert document["ora_corrente"] == "2026-11-12T10:30+00:00"
    assert document["tempo_dall_avvio"] == "2 ore e 30 minuti"


def test_the_user_message_has_the_state_of_the_flow() -> None:
    assert user_document(context())["stato_del_flusso"] == {
        "valuta": "USDC",
        "capitale_allocato": "400",
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
                "pnl_non_realizzato": "12.5",
                "prezzo_di_liquidazione": "41000",
            }
        ],
    }


def test_a_position_without_liquidation_price_says_so() -> None:
    cross = PositionView("ETH", TradeDirection.SHORT, Decimal(1), 1, Decimal(3000), Decimal(0), None)
    state = FlowStateView("USDC", Decimal(400), Decimal(250), Decimal(400), Decimal(0), (cross,))

    position = user_document(context(state=state))["stato_del_flusso"]

    assert isinstance(position, dict)
    assert position["posizioni_aperte"][0]["prezzo_di_liquidazione"] is None


def test_the_user_message_has_the_sources_with_their_weights_and_the_missing_data() -> None:
    document = user_document(context())

    assert document["fonti"] == [
        {"fonte": "indicatori", "peso": 7, "asset": "BTC", "valori": {"rsi_14": "61.2"}},
        {
            "fonte": "sentiment-alternative-me",
            "peso": 3,
            "asset": None,
            "valori": {"valore": "29", "classificazione": "Fear"},
        },
    ]
    assert document["dati_mancanti"] == ["forecast: servizio non raggiungibile"]


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
