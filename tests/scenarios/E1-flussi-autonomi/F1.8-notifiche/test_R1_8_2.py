import json
import logging
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.agent.errors import ModelCreditExhaustedError
from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.application.flows.remove_account_with_flows import RemoveAccountWithFlowsCommand
from autotrading.application.flows.stop_flow import StopFlowCommand
from autotrading.application.notifications.link_chat import LinkChatCommand
from autotrading.application.orders.close_position import ClosePositionCommand
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.cycles import FakeTransientError
from tests.support.activity import a_position, an_activity
from tests.support.flow_cycles import FlowCycles
from tests.support.notifications import chat_named
from tests.support.platform import HYPERLIQUID
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.8-notifiche/R1.8.2-notifiche-essenziali.feature")

# Capital and quota of the flow give a margin of 50 USDC: with leverage 3 the opening is worth 150 USDC.
CAPITAL = Decimal(1000)
QUOTA = 0.05
MID_PRICE = Decimal(100000)
OPENING_FEE = Decimal("0.07")
CYCLE = timedelta(minutes=15)


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def notified() -> dict[str, str]:
    """The text the scenario expects in the notification, read back for the chats that must not receive it."""
    return {}


def link(flow_cycles: FlowCycles, user: str, chat: str) -> None:
    platform = flow_cycles.platform
    code = platform.use_cases_of(user).request_link_code.execute().code
    platform.link_chat().execute(LinkChatCommand(chat_named(chat), code))
    # The confirmation of the link is R1.8.1: the scenarios read only what the flows notify.
    platform.messenger.sent.clear()


def answer(flow_cycles: FlowCycles, *decisions: dict[str, object]) -> None:
    flow_cycles.model.text = json.dumps({"decisioni": list(decisions)})


def opening(asset: str, leverage: int = 3) -> dict[str, object]:
    return {
        "asset": asset,
        "azione": "apri",
        "direzione": "long",
        "quota": QUOTA,
        "leva": leverage,
        "ragionamento": "r",
    }


def access_of(flow_cycles: FlowCycles, flow: str) -> TradingAccess:
    credentials = flow_cycles.credentials_of(flow)
    return TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)


def open_position(flow_cycles: FlowCycles, flow: str, asset: str, leverage: int = 3) -> None:
    flow_cycles.platform.order_exchange.fill_at = (MID_PRICE, OPENING_FEE)
    answer(flow_cycles, opening(asset, leverage))
    flow_cycles.run(flow)


# Given


@given(quoted('che "{user}" ha la chat "{chat}" collegata e il flusso "{flow}"'))
def chat_and_flow(flow_cycles: FlowCycles, user: str, chat: str, flow: str) -> None:
    link(flow_cycles, user, chat)
    flow_cycles.add_flow(user, flow)
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, allocated_capital=CAPITAL))


@given(quoted('che "{user}" ha la chat "{chat}" collegata'))
def chat_only(flow_cycles: FlowCycles, user: str, chat: str) -> None:
    link(flow_cycles, user, chat)


@given("che Telegram non risponde")
def telegram_unreachable(flow_cycles: FlowCycles) -> None:
    flow_cycles.platform.messenger.reachable = False


@given(quoted('che "{user}" ha scollegato la chat Telegram'))
def chat_unlinked(flow_cycles: FlowCycles, user: str) -> None:
    flow_cycles.platform.use_cases_of(user).unlink_chat.execute()


@given(quoted('che il flusso "{flow}" ha una posizione aperta su "{asset}"'))
def flow_with_open_position(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    open_position(flow_cycles, flow, asset)
    # The opening is notified on its own (see the examples above): the scenario reads only the closing.
    flow_cycles.platform.messenger.sent.clear()


# When: the events of the flow


@when(quoted('il flusso "{flow}" apre long su "{asset}" con leva {leverage} e valore {value} USDC'))
def flow_opens_long(flow_cycles: FlowCycles, flow: str, asset: str, leverage: str, value: str) -> None:
    open_position(flow_cycles, flow, asset, int(leverage))
    [order] = flow_cycles.platform.order_exchange.sent
    assert order.size * MID_PRICE == Decimal(value)


@when(quoted('il flusso "{flow}" apre una posizione su "{asset}"'))
def flow_opens(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    open_position(flow_cycles, flow, asset)


@when(quoted('il flusso "{flow}" chiude la posizione su "{asset}" con PnL {pnl} USDC'))
def flow_closes(flow_cycles: FlowCycles, flow: str, asset: str, pnl: str) -> None:
    exchange = flow_cycles.platform.order_exchange
    exchange.hold(access_of(flow_cycles, flow), HeldPosition(asset, Direction.LONG, Decimal("0.0015"), 3))
    exchange.realized_on_close = Decimal(pnl.replace(",", "."))
    answer(flow_cycles, {"asset": asset, "azione": "chiudi", "ragionamento": "r"})
    flow_cycles.run(flow)


@when(quoted('la posizione su "{asset}" del flusso "{flow}" si chiude per {reason} con PnL {pnl} USDC'))
def position_closes_for(flow_cycles: FlowCycles, asset: str, flow: str, reason: str, pnl: str) -> None:
    platform = flow_cycles.platform
    platform.order_exchange.realized_on_close = Decimal(pnl.replace(",", "."))
    operating = flow_cycles.flow(flow)
    owner = flow_cycles.users[flow]
    user_id = platform.user_id_of(owner)
    use_cases = platform.use_cases_of(owner)
    if reason == "decisione dell'agente":
        answer(flow_cycles, {"asset": asset, "azione": "chiudi", "ragionamento": "r"})
        # The opening took the cycle due now: the closing comes with the next one.
        flow_cycles.clock.current += CYCLE
        flow_cycles.run(flow)
    elif reason == "stop del flusso":
        use_cases.stop_flow.execute(StopFlowCommand(operating.id, user_id))
    elif reason == "rimozione del conto":
        use_cases.remove_account_with_flows.execute(
            RemoveAccountWithFlowsCommand(operating.assigned_account_id, user_id, confirmed=True)
        )
    else:
        assert reason == "comando manuale", reason
        use_cases.close_position.execute(ClosePositionCommand(operating.assigned_account_id, asset, user_id))


@when(quoted('un ciclo del flusso "{flow}" fallisce con il messaggio "{message}"'))
def cycle_fails(flow_cycles: FlowCycles, flow: str, message: str) -> None:
    flow_cycles.model.failure = FakeTransientError(message)
    flow_cycles.run(flow)


@when(quoted('l\'exchange rifiuta un ordine del flusso "{flow}" con "{message}"'))
def order_rejected(flow_cycles: FlowCycles, flow: str, message: str) -> None:
    flow_cycles.platform.order_exchange.rejection = message
    open_position(flow_cycles, flow, "BTC")


@when(quoted('il flusso "{flow}" va in pausa per "{reason}"'))
def flow_paused(flow_cycles: FlowCycles, flow: str, reason: str) -> None:
    error = ModelCreditExhaustedError(ProviderName("openrouter"))
    assert str(error) == reason
    flow_cycles.model.failure = error
    flow_cycles.run(flow)


@when(quoted('sul conto di "{flow}" compare una posizione non attribuibile su "{asset}"'))
def unattributable_position(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    address = flow_cycles.credentials_of(flow).account_address
    flow_cycles.platform.activity_reader.activities[address] = an_activity(positions=(a_position(asset),))
    flow_cycles.run(flow)


# Then


@then(quoted('la chat "{chat}" riceve una notifica che contiene "{text}"'))
def chat_receives(flow_cycles: FlowCycles, notified: dict[str, str], chat: str, text: str) -> None:
    notified["text"] = text
    received = flow_cycles.platform.messenger.received_by(chat_named(chat))
    assert any(text in message for message in received), received


@then(quoted('la chat "{chat}" riceve una sola notifica che contiene "{text}"'))
def chat_receives_once(flow_cycles: FlowCycles, chat: str, text: str) -> None:
    received = flow_cycles.platform.messenger.received_by(chat_named(chat))
    assert [message for message in received if "chiusa" in message] == [text], received


@then(quoted('lo storico del flusso "{flow}" contiene la posizione su "{asset}" con PnL {pnl} USDC'))
def history_with_pnl(flow_cycles: FlowCycles, flow: str, asset: str, pnl: str) -> None:
    operating = flow_cycles.flow(flow)
    use_cases = flow_cycles.platform.use_cases_of(flow_cycles.users[flow])
    [position] = use_cases.list_closed_positions.execute(ListClosedPositionsCommand(operating.id.value))
    assert (position.asset, position.pnl) == (asset, Decimal(pnl.replace(",", ".")))


@then(quoted('la chat "{chat}" non riceve la notifica'))
def chat_does_not_receive(flow_cycles: FlowCycles, notified: dict[str, str], chat: str) -> None:
    received = flow_cycles.platform.messenger.received_by(chat_named(chat))
    assert not any(notified["text"] in message for message in received)
    assert received == []


@then(quoted('il ciclo del flusso "{flow}" si conclude'))
def cycle_completes(flow_cycles: FlowCycles, flow: str) -> None:
    assert flow_cycles.last_record(flow).outcome is CycleOutcome.COMPLETED
    assert flow_cycles.platform.order_exchange.executions


@then("l'invio fallito della notifica è registrato")
def failed_sending_recorded(caplog: pytest.LogCaptureFixture) -> None:
    assert [
        record.getMessage()
        for record in caplog.records
        if record.name == "autotrading.notifications" and record.levelno == logging.WARNING
    ] == ["invio della notifica fallito"]


@then("nessuna notifica viene inviata")
def nothing_sent(flow_cycles: FlowCycles) -> None:
    assert flow_cycles.platform.messenger.sent == []
