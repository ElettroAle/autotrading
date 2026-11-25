"""R5.3.5: the memory of the flow gives the agent the motive of every decision, cut to the length the flow sets, the
course of the positions its openings opened, and only the decisions that open or close a position unless the flow
wants them all; the user reads it as the agent receives it, through the API and the MCP server. On the cycle the worker
composes and on the use cases of the API and of the MCP server, with the fake adapters (ADR
memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni).
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from pytest_bdd import given, then, when

from autotrading.application.flows.create_flow import CreateFlowCommand, MemoryRequest
from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.errors import MemoryTextLengthNotPositiveError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from tests.support.api_session import ApiSession
from tests.support.flow_cycles import at
from tests.support.flows import OPENROUTER_MODEL
from tests.support.mcp_session import McpSession, body_of
from tests.support.orders import EXECUTION
from tests.support.steps import quoted
from tests.support.steps_r5_3_4 import *  # noqa: F403 - the steps of R5.3.4 these scenarios share
from tests.support.steps_r5_3_4 import USER, MemoryCycles, entries_of

MOTIVE = "rottura di 95000 con volumi in crescita"
REASONING = "Il contesto di mercato è laterale da giorni; i volumi crescono e il prezzo rompe 95000."
MARKET_CONTEXT = "Il contesto di mercato"
INVALIDATION = "chiusura a 4 ore sotto 94000"
LONG_MOTIVE = ("la tesi regge finché il prezzo resta sopra la media a 20 periodi " * 6)[:300]
STOP_LOSS_PNL = Decimal("-2.32")
OPENED_PRICE = Decimal("0.002452")
UNLIMITED = "illimitata"
SWITCHED_ON = "accesa"
OPERATIVE = frozenset({DecisionAction.OPEN, DecisionAction.CLOSE, DecisionAction.REVERSE})
# 20 openings, closings and reversals, 3 updates and 50 decisions not to act, from the oldest: the newest twenty mix
# every kind of action.
OPERATIVE_CYCLE = (DecisionAction.OPEN, DecisionAction.CLOSE, DecisionAction.REVERSE)
HISTORY = (
    *("operative",) * 10,
    *("hold",) * 40,
    "update",
    *("operative",) * 5,
    "update",
    *("hold",) * 10,
    "update",
    *("operative",) * 5,
)


@dataclass
class MemoryImprovements:
    """The memory cycles of R5.3.4, with what the user and the client of the MCP server got and the decisions in
    history order."""

    memory: MemoryCycles = field(default_factory=MemoryCycles)
    history: list[tuple[datetime, DecisionAction]] = field(default_factory=list)
    created: Flow | None = None
    read: Flow | None = None
    refused: AutotradingError | None = None
    version_before: int = 0
    mcp_body: dict[str, Any] = field(default_factory=dict)

    @property
    def remembered(self) -> tuple[AssetMemory, ...] | None:
        return self.memory.remembered


@pytest.fixture
def improvements(memory_cycles: MemoryCycles) -> MemoryImprovements:
    return MemoryImprovements(memory=memory_cycles)


def received_on(improvements: MemoryImprovements, asset: str) -> tuple[MemoryEntry, ...]:
    return entries_of(improvements.memory.received("alfa"), asset)


def a_decision(asset: str, action: DecisionAction, motive: str, reasoning: str = REASONING) -> RecordedDecision:
    direction = TradeSide.LONG if action is DecisionAction.OPEN else None
    invalidation = INVALIDATION if action is DecisionAction.OPEN else None
    return RecordedDecision(asset, action, direction, 70, reasoning, motive=motive, invalidation=invalidation)


def closed_by_the_stop_loss(memory: MemoryCycles, name: str, asset: str, minutes: int) -> None:
    """An opening executed at its price whose position the stop loss closed the minutes given after it opened."""
    planned_at = at("08:00")
    flow = memory.flow(name)
    memory.decided(name, planned_at, a_decision(asset, DecisionAction.OPEN, MOTIVE))
    market_order = MarketOrder.opening(asset, Direction.LONG, Decimal(1000), Slippage.default())
    request = OrderRequest(
        flow.assigned_account_id,
        OrderSource(OrderOrigin.FLOW, flow=FlowLink(flow.id.value, planned_at, asset)),
        2,
        market_order,
    )
    execution = replace(EXECUTION, average_price=OPENED_PRICE, executed_at=planned_at)
    memory.cycles.platform.orders_of(flow.tenant_id).add(Order.executed(request, execution))
    closed_at = planned_at + timedelta(minutes=minutes)
    memory.cycles.platform.closed_positions.positions.append(
        ClosedPosition(
            tenant_id=flow.tenant_id,
            flow_id=flow.id,
            asset=asset,
            side=TradeSide.LONG,
            leverage=2,
            margin=Decimal(50),
            opening=PositionEnd(OPENED_PRICE, planned_at, planned_at),
            closing=PositionEnd(Decimal("0.0024"), closed_at),
            fees=Decimal("0.1"),
            reason=CloseReason.STOP_LOSS,
            realized_pnl=STOP_LOSS_PNL,
        )
    )


def expected_stop_loss_line(course: str) -> str:
    return f"apri long, prezzo {OPENED_PRICE}, {course}, PnL realizzato {STOP_LOSS_PNL}: {MOTIVE}"


# Given


@given(quoted('che il flusso "{flow}" ha la memoria attiva con lunghezza {length}'))
def memory_with_length(improvements: MemoryImprovements, flow: str, length: str) -> None:
    text_length = None if length == UNLIMITED else int(length)
    improvements.memory.remember(flow, FlowMemory(active=True, text_length=text_length))


@given(quoted('che il flusso "{flow}" ha la memoria attiva con {decisions} decisioni e «tutte le decisioni» {state}'))
def memory_with_choice(improvements: MemoryImprovements, flow: str, decisions: str, state: str) -> None:
    memory = FlowMemory(active=True, decisions=int(decisions), all_decisions=state == SWITCHED_ON)
    improvements.memory.remember(flow, memory)


@given(
    quoted('che "{flow}" ha deciso su "{asset}" con un motivo e un ragionamento che comincia dal contesto di mercato')
)
def decided_with_motive(improvements: MemoryImprovements, flow: str, asset: str) -> None:
    improvements.memory.decided(flow, at("08:00"), a_decision(asset, DecisionAction.OPEN, MOTIVE))


@given(quoted('che "{flow}" ha deciso su "{asset}" con un motivo di {length} caratteri'))
def decided_with_long_motive(improvements: MemoryImprovements, flow: str, asset: str, length: str) -> None:
    assert len(LONG_MOTIVE) == int(length)
    improvements.memory.decided(flow, at("08:00"), a_decision(asset, DecisionAction.CLOSE, LONG_MOTIVE))


@given(
    quoted(
        'che una posizione aperta da "{flow}" su "{asset}" è stata chiusa dallo stop loss {minutes} minuti dopo'
        " l'apertura"
    )
)
def position_closed_by_the_stop_loss(improvements: MemoryImprovements, flow: str, asset: str, minutes: str) -> None:
    closed_by_the_stop_loss(improvements.memory, flow, asset, int(minutes))


@given(
    quoted(
        'che "{flow}" ha su "{asset}" {operative} tra aperture, chiusure e inversioni più {updates} aggiornamenti e'
        " {holds} mantieni"
    )
)
def history_of_every_kind(  # noqa: PLR0917 - one argument per value of the step
    improvements: MemoryImprovements, flow: str, asset: str, operative: str, updates: str, holds: str
) -> None:
    assert (HISTORY.count("operative"), HISTORY.count("update"), HISTORY.count("hold")) == (
        int(operative),
        int(updates),
        int(holds),
    )
    now = improvements.memory.cycles.clock.now()
    kinds = {"hold": DecisionAction.HOLD, "update": DecisionAction.UPDATE}
    for index, kind in enumerate(HISTORY):
        action = OPERATIVE_CYCLE[index % len(OPERATIVE_CYCLE)] if kind == "operative" else kinds[kind]
        planned_at = now - timedelta(minutes=30 * (len(HISTORY) - index))
        improvements.memory.decided(flow, planned_at, a_decision(asset, action, f"motivo {index}"))
        improvements.history.append((planned_at, action))


@given(quoted('che il flusso "{flow}" esisteva prima delle nuove impostazioni, con la memoria {state}'))
def flow_from_before(improvements: MemoryImprovements, flow: str, state: str) -> None:
    # A version saved before knew only whether the memory was on, its decisions and its days.
    improvements.memory.remember(flow, FlowMemory(state == "attiva", 10, 30))


# When


@when(quoted('"{user}" crea un flusso senza indicare le nuove impostazioni della memoria'))
def creates_without_the_new_settings(improvements: MemoryImprovements, user: str) -> None:
    cycles = improvements.memory.cycles
    command = CreateFlowCommand(
        name="gamma",
        account_id=cycles.account_of(user),
        assets=("SOL",),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
        memory=MemoryRequest(active=True, decisions=5, days=14),
    )
    cycles.register_key(cycles.platform.tenant_of(user), OPENROUTER_MODEL.partition("/")[0])
    improvements.created = cycles.platform.use_cases_of(user).create_flow.execute(command)


@when(quoted('"{user}" legge la configurazione di "{flow}"'))
def reads_the_configuration(improvements: MemoryImprovements, user: str, flow: str) -> None:
    command = GetFlowCommand(improvements.memory.flow(flow).id)
    improvements.read = improvements.memory.cycles.platform.use_cases_of(user).get_flow.execute(command)


@when(quoted('"{user}" imposta la lunghezza della memoria di "{flow}" a {length}'))
def sets_the_length(improvements: MemoryImprovements, user: str, flow: str, length: str) -> None:
    current = improvements.memory.flow(flow)
    improvements.version_before = current.configuration.version
    command = ModifyFlowCommand(current.id, memory=MemoryRequest(text_length=int(length)))
    try:
        improvements.memory.cycles.platform.use_cases_of(user).modify_flow.execute(command)
    except AutotradingError as error:
        improvements.refused = error


@when(quoted('il client MCP di "{user}" legge la memoria di "{flow}"'))
def mcp_reads_the_memory(improvements: MemoryImprovements, user: str, flow: str) -> None:
    platform = improvements.memory.cycles.platform
    platform.now = improvements.memory.cycles.clock.now()
    flow_id = str(improvements.memory.flow(flow).id.value)
    improvements.mcp_body = body_of(McpSession(platform).call_as(user, "read_flow_memory", {"flow_id": flow_id}))


# Then


@then(quoted('l\'agente riceve per la decisione su "{asset}" il motivo in una frase'))
def motive_received(improvements: MemoryImprovements, asset: str) -> None:
    [entry] = received_on(improvements, asset)
    assert entry.motive == MOTIVE
    assert f"- {entry.text}" in improvements.memory.cycles.system_text()
    assert entry.text.endswith(f": {MOTIVE}; invalidazione: {INVALIDATION}")


@then("l'agente non riceve l'inizio del ragionamento")
def reasoning_not_received(improvements: MemoryImprovements) -> None:
    assert MARKET_CONTEXT not in improvements.memory.cycles.system_text()


@then(quoted('il motivo su "{asset}" arriva lungo {length} caratteri e finisce con "{end}"'))
def motive_cut(improvements: MemoryImprovements, asset: str, length: str, end: str) -> None:
    [entry] = received_on(improvements, asset)
    assert len(entry.motive) == int(length)
    assert entry.motive.endswith(end)
    assert entry.motive == LONG_MOTIVE[: int(length) - len(end)] + end
    assert f"- {entry.text}" in improvements.memory.cycles.system_text()


@then(quoted('il motivo su "{asset}" arriva intero'))
def motive_whole(improvements: MemoryImprovements, asset: str) -> None:
    [entry] = received_on(improvements, asset)
    assert entry.motive == LONG_MOTIVE
    assert f": {LONG_MOTIVE}" in improvements.memory.cycles.system_text()


@then(quoted('l\'apertura su "{asset}" compare in memoria con "{course}"'))
def opening_with_its_course(improvements: MemoryImprovements, asset: str, course: str) -> None:
    [entry] = received_on(improvements, asset)
    assert entry.outcome is not None
    assert entry.outcome.course == course
    assert expected_stop_loss_line(course) in improvements.memory.cycles.system_text()


@then("con il suo PnL realizzato")
def with_its_realized_pnl(improvements: MemoryImprovements) -> None:
    [entry] = received_on(improvements, "BTC")
    assert entry.outcome is not None
    assert (entry.outcome.pnl, entry.outcome.realized) == (STOP_LOSS_PNL, True)
    assert f"PnL realizzato {STOP_LOSS_PNL}" in improvements.memory.cycles.system_text()


@then(quoted('la memoria su "{asset}" mostra le {count} aperture, chiusure e inversioni'))
def only_the_operative(improvements: MemoryImprovements, asset: str, count: str) -> None:
    entries = received_on(improvements, asset)
    operative = [planned_at for planned_at, action in reversed(improvements.history) if action in OPERATIVE]
    assert len(operative) == int(count)
    assert [entry.planned_at for entry in entries] == operative


@then(quoted('la memoria su "{asset}" non mostra nessun aggiornamento o mantieni'))
def no_update_nor_hold(improvements: MemoryImprovements, asset: str) -> None:
    entries = received_on(improvements, asset)
    assert all(entry.action in OPERATIVE for entry in entries)
    system = improvements.memory.cycles.system_text()
    assert f" {DecisionAction.HOLD.value}:" not in system
    assert f" {DecisionAction.UPDATE.value}:" not in system


@then(quoted('la memoria su "{asset}" mostra le ultime {count} decisioni, qualunque sia l\'azione'))
def the_latest_whatever_the_action(improvements: MemoryImprovements, asset: str, count: str) -> None:
    entries = received_on(improvements, asset)
    latest = list(reversed(improvements.history))[: int(count)]
    assert [(entry.planned_at, entry.action) for entry in entries] == latest
    assert {DecisionAction.HOLD, DecisionAction.UPDATE} <= {entry.action for entry in entries}
    system = improvements.memory.cycles.system_text()
    assert all(f"- {entry.text}" in system for entry in entries)


@then(quoted("la memoria del flusso ha lunghezza {length}"))
def created_with_length(improvements: MemoryImprovements, length: str) -> None:
    assert improvements.created is not None
    assert improvements.created.configuration.memory.text_length == int(length)


@then("la memoria del flusso ha «tutte le decisioni» spenta")
def created_without_every_decision(improvements: MemoryImprovements) -> None:
    assert improvements.created is not None
    assert improvements.created.configuration.memory.all_decisions is False


@then(quoted('la memoria di "{flow}" ha lunghezza {length}'))
def read_with_length(improvements: MemoryImprovements, flow: str, length: str) -> None:
    assert improvements.read is not None
    assert improvements.read.name.value == flow
    assert improvements.read.configuration.memory.text_length == int(length)


@then(quoted('la memoria di "{flow}" ha «tutte le decisioni» spenta'))
def read_without_every_decision(improvements: MemoryImprovements, flow: str) -> None:
    assert improvements.read is not None
    assert improvements.read.name.value == flow
    assert improvements.read.configuration.memory.all_decisions is False


@then("la modifica è rifiutata con il motivo")
def length_refused(improvements: MemoryImprovements) -> None:
    refused = improvements.refused
    assert isinstance(refused, MemoryTextLengthNotPositiveError)
    assert str(refused) == "la lunghezza del motivo della memoria è un intero positivo"
    assert refused.details == {"field": "memory.text_length"}


@then(quoted('"{flow}" resta alla versione in vigore'))
def version_kept(improvements: MemoryImprovements, flow: str) -> None:
    assert improvements.memory.cycles.flow(flow).configuration.version == improvements.version_before


@then(quoted('vede per "{asset}" le voci come le riceve l\'agente'))
def read_as_received(improvements: MemoryImprovements, asset: str) -> None:
    [entry] = entries_of(improvements.remembered, asset)
    assert expected_stop_loss_line("chiusa dallo stop loss dopo 12 minuti") in entry.text
    improvements.memory.cycles.run("alfa")
    assert entries_of(improvements.memory.received("alfa"), asset) == (entry,)


@then(quoted('riceve per "{asset}" le voci come le riceve l\'agente'))
def mcp_entries_as_received(improvements: MemoryImprovements, asset: str) -> None:
    [remembered] = [each for each in improvements.mcp_body["assets"] if each["asset"] == asset]
    [entry] = remembered["entries"]
    assert (entry["motive"], entry["invalidation"]) == (MOTIVE, INVALIDATION)
    assert entry["outcome"] == {
        "pnl": str(STOP_LOSS_PNL),
        "realized": True,
        "course": "chiusa dallo stop loss dopo 12 minuti",
    }


@then("le voci sono quelle che risponde l'API")
def mcp_entries_as_the_api(improvements: MemoryImprovements) -> None:
    flow_id = improvements.memory.flow("alfa").id.value
    answered = ApiSession(improvements.memory.cycles.platform).get_as(USER, f"/flows/{flow_id}/memory").json()
    assert answered == improvements.mcp_body
