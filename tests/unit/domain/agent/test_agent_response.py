import json
from decimal import Decimal

import pytest

from autotrading.domain.agent.agent_response import AgentResponse
from autotrading.domain.agent.decision import Decision, DiscardedDecision, TradeAction, TradeDirection, TradeOpening
from autotrading.domain.agent.exit_plan import ExitPlan, ExitPlanChange

ASSETS = ("BTC", "ETH", "SOL")


def answer(*decisions: object) -> str:
    return json.dumps({"decisioni": list(decisions)})


def opening(asset: str = "BTC", **fields: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "asset": asset,
        "azione": "apri",
        "direzione": "long",
        "quota": 0.1,
        "leva": 3,
        "obiettivo": None,
        "stop": None,
        "invalidazione": None,
        "confidenza": 75,
        "ragionamento": "rottura della resistenza",
    }
    decision.update(fields)
    return {key: value for key, value in decision.items() if value is not ...}


def update(asset: str = "BTC", **fields: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "asset": asset,
        "azione": "aggiorna",
        "direzione": None,
        "quota": None,
        "leva": None,
        "obiettivo": None,
        "stop": None,
        "invalidazione": None,
        "togli_obiettivo": False,
        "confidenza": 80,
        "ragionamento": "proteggo il guadagno",
    }
    decision.update(fields)
    return {key: value for key, value in decision.items() if value is not ...}


def read(raw: str) -> AgentResponse:
    return AgentResponse.read(raw, ASSETS)


def reasons(response: AgentResponse) -> dict[str, str]:
    return {discarded.asset: discarded.reason for discarded in response.discarded}


def test_one_decision_for_each_asset() -> None:
    response = read(
        answer(
            opening(),
            {"asset": "ETH", "azione": "chiudi", "confidenza": 60, "ragionamento": "obiettivo raggiunto"},
            {"asset": "SOL", "azione": "mantieni", "confidenza": 50, "ragionamento": "mercato laterale"},
        )
    )

    assert [(decision.asset, decision.action) for decision in response.decisions] == [
        ("BTC", TradeAction.OPEN),
        ("ETH", TradeAction.CLOSE),
        ("SOL", TradeAction.HOLD),
    ]
    assert (response.discarded, response.missing) == ((), ())


def test_an_opening_keeps_its_fields_and_reasoning() -> None:
    decision = read(answer(opening(direzione="short"))).decisions[0]

    assert decision == Decision(
        "BTC",
        TradeAction.OPEN,
        "rottura della resistenza",
        75,
        TradeOpening(TradeDirection.SHORT, Decimal("0.1"), 3),
    )


@pytest.mark.parametrize("action", ["mantieni", "chiudi"])
def test_hold_and_close_ignore_the_operational_fields(action: str) -> None:
    response = read(answer(opening("SOL", azione=action, leva=10, quota="tanta", ragionamento="mercato laterale")))

    assert response.decisions == (Decision("SOL", TradeAction(action), "mercato laterale", 75),)


def test_an_opening_keeps_its_exit_plan() -> None:
    entry = opening(obiettivo=63000, stop=58500.5, invalidazione="  chiusura a 4 ore sotto 59000 ")

    decision = read(answer(entry)).decisions[0]

    assert decision.opening is not None
    assert decision.opening.exit_plan == ExitPlan(Decimal(63000), Decimal("58500.5"), "chiusura a 4 ore sotto 59000")


def test_every_part_of_the_exit_plan_is_optional() -> None:
    decision = read(answer(opening(obiettivo=None, stop=None, invalidazione=None))).decisions[0]

    assert decision.opening is not None
    assert decision.opening.exit_plan == ExitPlan()


def test_a_blank_invalidation_is_no_invalidation() -> None:
    decision = read(answer(opening(invalidazione="   "))).decisions[0]

    assert decision.opening is not None
    assert decision.opening.exit_plan.invalidation is None


def test_hold_and_close_ignore_the_exit_plan() -> None:
    response = read(answer(opening("SOL", azione="mantieni", obiettivo="alto", stop=-3, invalidazione=1)))

    assert response.decisions == (Decision("SOL", TradeAction.HOLD, "rottura della resistenza", 75),)


def test_the_asset_is_read_in_upper_case_and_the_texts_without_spaces() -> None:
    decision = read(answer(opening(" btc ", ragionamento="  rottura  "))).decisions[0]

    assert (decision.asset, decision.reasoning) == ("BTC", "rottura")


def test_only_the_non_conforming_decisions_are_discarded() -> None:
    response = read(answer(opening(), opening("ETH", direzione=...)))

    assert reasons(response) == {"ETH": "campo obbligatorio mancante: direzione"}
    assert [decision.asset for decision in response.decisions] == ["BTC"]


@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        ({"quota": 1.5}, "valore fuori dall'intervallo: quota"),
        ({"quota": -0.1}, "valore fuori dall'intervallo: quota"),
        ({"quota": "tanta"}, "valore di tipo non ammesso: quota"),
        ({"quota": True}, "valore di tipo non ammesso: quota"),
        ({"quota": ...}, "campo obbligatorio mancante: quota"),
        ({"leva": 0}, "valore fuori dall'intervallo: leva"),
        ({"leva": 2.5}, "valore di tipo non ammesso: leva"),
        ({"leva": "3"}, "valore di tipo non ammesso: leva"),
        ({"leva": True}, "valore di tipo non ammesso: leva"),
        ({"leva": None}, "campo obbligatorio mancante: leva"),
        ({"direzione": "sideways"}, "valore non ammesso: direzione"),
        ({"direzione": 1}, "valore di tipo non ammesso: direzione"),
        ({"azione": "raddoppia"}, "azione non ammessa: raddoppia"),
        ({"azione": ...}, "campo obbligatorio mancante: azione"),
        ({"azione": ["apri"]}, "valore di tipo non ammesso: azione"),
        ({"ragionamento": ...}, "campo obbligatorio mancante: ragionamento"),
        ({"ragionamento": "   "}, "campo obbligatorio mancante: ragionamento"),
        ({"obiettivo": 0}, "valore fuori dall'intervallo: obiettivo"),
        ({"obiettivo": -1}, "valore fuori dall'intervallo: obiettivo"),
        ({"obiettivo": "alto"}, "valore di tipo non ammesso: obiettivo"),
        ({"obiettivo": True}, "valore di tipo non ammesso: obiettivo"),
        ({"stop": 0}, "valore fuori dall'intervallo: stop"),
        ({"stop": "58500"}, "valore di tipo non ammesso: stop"),
        ({"stop": False}, "valore di tipo non ammesso: stop"),
        ({"invalidazione": 59000}, "valore di tipo non ammesso: invalidazione"),
        # The rigid schema wants every key: an opening without one is not conforming (ADR
        # piano-di-uscita-nella-decisione-dell-agente).
        ({"obiettivo": ...}, "campo obbligatorio mancante: obiettivo"),
        ({"stop": ...}, "campo obbligatorio mancante: stop"),
        ({"invalidazione": ...}, "campo obbligatorio mancante: invalidazione"),
        # The confidence is an integer from 0 to 100 in every decision (R3.1.4).
        ({"confidenza": ...}, "campo obbligatorio mancante: confidenza"),
        ({"confidenza": None}, "campo obbligatorio mancante: confidenza"),
        ({"confidenza": -1}, "valore fuori dall'intervallo: confidenza"),
        ({"confidenza": 101}, "valore fuori dall'intervallo: confidenza"),
        ({"confidenza": 75.5}, "valore di tipo non ammesso: confidenza"),
        ({"confidenza": "75"}, "valore di tipo non ammesso: confidenza"),
        ({"confidenza": True}, "valore di tipo non ammesso: confidenza"),
    ],
)
def test_the_reasons_of_non_conformity(fields: dict[str, object], reason: str) -> None:
    assert reasons(read(answer(opening("BTC", **fields)))) == {"BTC": reason}


@pytest.mark.parametrize(("fraction", "expected"), [(0, Decimal(0)), (1, Decimal(1)), (0.25, Decimal("0.25"))])
def test_the_share_of_capital_goes_from_0_to_1(fraction: float, expected: Decimal) -> None:
    decision = read(answer(opening(quota=fraction))).decisions[0]

    assert decision.opening is not None
    assert decision.opening.margin_fraction == expected


def test_a_decision_on_an_asset_outside_the_flow_is_discarded() -> None:
    assert reasons(read(answer(opening(), opening("DOGE")))) == {"DOGE": "asset non del flusso: DOGE"}


@pytest.mark.parametrize("entry", [{"azione": "apri"}, {"asset": 7, "azione": "apri"}, {"asset": " "}, "BTC apri", 3])
def test_a_decision_without_asset_is_discarded(entry: object) -> None:
    response = read(answer(entry))

    assert response.discarded == (DiscardedDecision("", "campo obbligatorio mancante: asset"),)
    assert response.missing == ASSETS


def test_an_asset_without_decision_is_missing() -> None:
    response = read(answer(opening(), opening("ETH")))

    assert response.missing == ("SOL",)


def test_a_discarded_asset_is_not_missing() -> None:
    response = read(answer(opening("BTC", leva=0)))

    assert response.missing == ("ETH", "SOL")


def test_two_decisions_on_the_same_asset_are_both_discarded() -> None:
    response = read(answer(opening(), opening("BTC", azione="chiudi"), opening("ETH")))

    assert response.discarded == (
        DiscardedDecision("BTC", "decisione ripetuta per l'asset: BTC"),
        DiscardedDecision("BTC", "decisione ripetuta per l'asset: BTC"),
    )
    assert [decision.asset for decision in response.decisions] == ["ETH"]


@pytest.mark.parametrize(
    "raw",
    [
        "Comprerei BTC, il mercato sale.",
        "",
        '{"decisioni": "apri BTC"}',
        '{"decisions": []}',
        '[{"asset": "BTC"}]',
        "```",
        '{"decisioni": [',
    ],
)
def test_an_unreadable_answer_discards_every_decision(raw: str) -> None:
    response = read(raw)

    assert response.raw == raw
    assert response.decisions == ()
    assert response.discarded == tuple(DiscardedDecision(asset, "risposta non leggibile") for asset in ASSETS)
    assert response.missing == ()


@pytest.mark.parametrize("fence", ["```json\n{}\n```", "```\n{}\n```", "  ```json\n{}\n```  "])
def test_an_answer_in_a_code_block_is_read(fence: str) -> None:
    raw = fence.replace("{}", answer(opening()))

    response = read(raw)

    assert [decision.asset for decision in response.decisions] == ["BTC"]
    assert response.raw == raw


def test_an_empty_list_leaves_every_asset_missing() -> None:
    assert read(answer()).missing == ASSETS


def test_an_update_carries_the_change_of_the_plan() -> None:
    decision = read(answer(update(obiettivo=68000, stop=62000.5, invalidazione=" chiusura sotto 61000 "))).decisions[0]

    assert decision == Decision(
        "BTC",
        TradeAction.UPDATE,
        "proteggo il guadagno",
        80,
        plan_change=ExitPlanChange(Decimal(68000), Decimal("62000.5"), "chiusura sotto 61000"),
    )


def test_an_update_may_remove_the_target() -> None:
    decision = read(answer(update(togli_obiettivo=True))).decisions[0]

    assert decision.plan_change == ExitPlanChange(remove_target=True)


def test_a_null_removal_of_the_target_keeps_it() -> None:
    decision = read(answer(update(stop=62000, togli_obiettivo=None))).decisions[0]

    assert decision.plan_change == ExitPlanChange(stop=Decimal(62000))


def test_an_update_ignores_the_fields_of_an_opening() -> None:
    decision = read(answer(update(direzione="long", quota=0.5, leva=3, stop=62000))).decisions[0]

    assert (decision.opening, decision.plan_change) == (None, ExitPlanChange(stop=Decimal(62000)))


@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        ({"stop": 0}, "valore fuori dall'intervallo: stop"),
        ({"obiettivo": "alto"}, "valore di tipo non ammesso: obiettivo"),
        ({"invalidazione": 1}, "valore di tipo non ammesso: invalidazione"),
        ({"togli_obiettivo": "si"}, "valore di tipo non ammesso: togli_obiettivo"),
        ({"togli_obiettivo": 1}, "valore di tipo non ammesso: togli_obiettivo"),
        ({"stop": ...}, "campo obbligatorio mancante: stop"),
        ({"togli_obiettivo": ...}, "campo obbligatorio mancante: togli_obiettivo"),
        # A new target and its removal together say two opposite things.
        ({"obiettivo": 68000, "togli_obiettivo": True}, "valore non ammesso: togli_obiettivo"),
    ],
)
def test_the_reasons_of_non_conformity_of_an_update(fields: dict[str, object], reason: str) -> None:
    assert reasons(read(answer(update("BTC", **fields)))) == {"BTC": reason}


@pytest.mark.parametrize("confidence", [0, 60, 100])
def test_a_decision_keeps_its_confidence_from_0_to_100(confidence: int) -> None:
    assert read(answer(opening(confidenza=confidence))).decisions[0].confidence == confidence


@pytest.mark.parametrize("action", ["mantieni", "chiudi", "aggiorna"])
def test_every_action_needs_its_confidence(action: str) -> None:
    response = read(answer(update("BTC", azione=action, confidenza=...)))

    assert reasons(response) == {"BTC": "campo obbligatorio mancante: confidenza"}
