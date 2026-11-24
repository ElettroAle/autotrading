"""R5.3.4: with the memory of the flow on, the agent receives in its system prompt the previous operative decisions of
the flow on every asset with their outcome, as many and as old as the flow sets; the user reads the memory of the flow
and changes it in a new version. On the cycle the worker composes and on the use cases of the API, with the fake
adapters (ADR memoria-del-flusso-dalle-decisioni-operative-precedenti).
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, then, when

from autotrading.application.flows.create_flow import CreateFlowCommand, MemoryRequest
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.read_flow_memory import ReadFlowMemoryCommand
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.system_prompt import MEMORY_HEADING
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from tests.support.flow_cycles import FlowCycles, at
from tests.support.flows import OPENROUTER_MODEL
from tests.support.orders import EXECUTION
from tests.support.steps import quoted

USER = "anna"
OPENED_PRICE = Decimal(95000)
REALIZED_PNL = Decimal(40)
OPENING_REASONING = "rottura della resistenza"


@dataclass
class MemoryCycles:
    """The flows of anna with the decisions their previous cycles recorded, and what the user read or changed."""

    cycles: FlowCycles = field(default_factory=FlowCycles)
    remembered: tuple[AssetMemory, ...] | None = None
    created: Flow | None = None
    version_before: int = 0

    def flow(self, name: str) -> Flow:
        if name not in self.cycles.users:
            self.cycles.add_flow(USER, name, assets=("BTC",))
        return self.cycles.flow(name)

    def remember(self, name: str, memory: FlowMemory) -> None:
        self.flow(name)
        self.cycles.reconfigure(name, lambda configuration: replace(configuration, memory=memory))

    def decided(self, name: str, planned_at: datetime, *decisions: RecordedDecision) -> None:
        record = CycleRecord(self.flow(name).id.value, planned_at, CycleOutcome.COMPLETED, decisions=decisions)
        self.cycles.records.record(record)

    def opened_and_closed(self, name: str, planned_at: datetime, asset: str) -> None:
        """An opening executed at its price whose position the flow closed with a realized PnL."""
        flow = self.flow(name)
        self.decided(
            name, planned_at, RecordedDecision(asset, DecisionAction.OPEN, TradeSide.LONG, 80, OPENING_REASONING)
        )
        market_order = MarketOrder.opening(asset, Direction.LONG, Decimal("0.001"), Slippage.default())
        source = OrderSource(OrderOrigin.FLOW, flow=FlowLink(flow.id.value, planned_at, asset))
        request = OrderRequest(flow.assigned_account_id, source, 2, market_order)
        execution = replace(EXECUTION, average_price=OPENED_PRICE, executed_at=planned_at)
        self.cycles.platform.orders_of(flow.tenant_id).add(Order.executed(request, execution))
        closed_at = planned_at + timedelta(minutes=30)
        self.cycles.platform.closed_positions.positions.append(
            ClosedPosition(
                tenant_id=flow.tenant_id,
                flow_id=flow.id,
                asset=asset,
                side=TradeSide.LONG,
                leverage=2,
                margin=Decimal(50),
                opening=PositionEnd(OPENED_PRICE, planned_at, planned_at),
                closing=PositionEnd(Decimal(96000), closed_at, closed_at),
                fees=Decimal("0.1"),
                reason=CloseReason.AGENT,
                realized_pnl=REALIZED_PNL,
            )
        )

    def received(self, name: str) -> tuple[AssetMemory, ...] | None:
        return self.cycles.last_record(name).memory


@pytest.fixture
def memory_cycles() -> MemoryCycles:
    return MemoryCycles()


def entries_of(memory: tuple[AssetMemory, ...] | None, asset: str) -> tuple[MemoryEntry, ...]:
    assert memory is not None
    [remembered] = [each for each in memory if each.asset == asset]
    return remembered.entries


def assert_the_opening_with_its_outcome(entry: MemoryEntry) -> None:
    assert (entry.action, entry.direction, entry.price, entry.reasoning) == (
        DecisionAction.OPEN,
        TradeSide.LONG,
        OPENED_PRICE,
        OPENING_REASONING,
    )
    assert entry.outcome == MemoryOutcome(REALIZED_PNL, realized=True)


# Given


@given(quoted('che il flusso "{flow}" ha la memoria attiva'))
def memory_on(memory_cycles: MemoryCycles, flow: str) -> None:
    memory_cycles.remember(flow, FlowMemory(active=True))


@given(quoted('che il flusso "{flow}" ha la memoria non attiva'))
def memory_off(memory_cycles: MemoryCycles, flow: str) -> None:
    memory_cycles.flow(flow)
    assert not memory_cycles.cycles.flow(flow).configuration.memory.active


@given(quoted('che il flusso "{flow}" ha la memoria attiva con {decisions} decisioni e {days} giorni'))
def memory_on_with_width(memory_cycles: MemoryCycles, flow: str, decisions: str, days: str) -> None:
    memory_cycles.remember(flow, FlowMemory(active=True, decisions=int(decisions), days=int(days)))


@given(quoted('che "{flow}" ha decisioni precedenti su "{asset}"'))
def previous_decisions(memory_cycles: MemoryCycles, flow: str, asset: str) -> None:
    memory_cycles.opened_and_closed(flow, at("08:00"), asset)


@given(
    quoted(
        'che "{flow}" ha {recent} decisioni operative su "{asset}" negli ultimi {days} giorni e una di {old} giorni fa'
    )
)
def decisions_in_and_out_of_the_window(  # noqa: PLR0917 - one argument per value of the step
    memory_cycles: MemoryCycles, flow: str, recent: str, asset: str, days: str, old: str
) -> None:
    now = at("10:00")
    for day in range(1, int(recent) + 1):
        assert day < int(days)
        decision = RecordedDecision(asset, DecisionAction.UPDATE, None, 60, f"stop di {day} giorni fa")
        memory_cycles.decided(flow, now - timedelta(days=day), decision)
    decision = RecordedDecision(asset, DecisionAction.CLOSE, None, 60, f"chiusura di {old} giorni fa")
    memory_cycles.decided(flow, now - timedelta(days=int(old)), decision)


@given(quoted('che "{flow}" ha deciso di non agire su "{asset}" nell\'ultimo ciclo'))
def held_in_the_last_cycle(memory_cycles: MemoryCycles, flow: str, asset: str) -> None:
    memory_cycles.opened_and_closed(flow, at("08:00"), asset)
    memory_cycles.decided(flow, at("09:45"), RecordedDecision(asset, DecisionAction.HOLD, None, 50, "mercato laterale"))


@given(quoted('che il flusso "{flow}" dello stesso conto ha decisioni su "{asset}"'))
def other_flow_decided(memory_cycles: MemoryCycles, flow: str, asset: str) -> None:
    memory_cycles.cycles.add_flow(USER, flow, assets=("ETH",))
    decision = RecordedDecision(asset, DecisionAction.CLOSE, None, 70, f"chiusura di {flow}")
    memory_cycles.decided(flow, at("09:00"), decision)


# When


@when(quoted('parte il ciclo di "{flow}"'))
def cycle_starts(memory_cycles: MemoryCycles, flow: str) -> None:
    memory_cycles.cycles.run(flow)


@when(quoted('"{user}" crea un flusso senza indicare la memoria'))
def creates_without_memory(memory_cycles: MemoryCycles, user: str) -> None:
    cycles = memory_cycles.cycles
    command = CreateFlowCommand(
        name="gamma",
        account_id=cycles.account_of(user),
        assets=("SOL",),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
    )
    cycles.register_key(cycles.platform.tenant_of(user), OPENROUTER_MODEL.partition("/")[0])
    memory_cycles.created = cycles.platform.use_cases_of(user).create_flow.execute(command)


@when(quoted('"{user}" apre la memoria di "{flow}"'))
def opens_memory(memory_cycles: MemoryCycles, user: str, flow: str) -> None:
    command = ReadFlowMemoryCommand(memory_cycles.flow(flow).id)
    # The API reads at the instant of the cycles of the scenario.
    memory_cycles.cycles.platform.now = memory_cycles.cycles.clock.now()
    memory_cycles.remembered = memory_cycles.cycles.platform.use_cases_of(user).read_flow_memory.execute(command)


@when(quoted('"{user}" attiva la memoria di "{flow}" con {decisions} decisioni e {days} giorni'))
def turns_memory_on(memory_cycles: MemoryCycles, user: str, flow: str, decisions: str, days: str) -> None:
    current = memory_cycles.flow(flow)
    memory_cycles.version_before = current.configuration.version
    memory = MemoryRequest(active=True, decisions=int(decisions), days=int(days))
    command = ModifyFlowCommand(current.id, memory=memory)
    memory_cycles.cycles.platform.use_cases_of(user).modify_flow.execute(command)


# Then


@then(quoted('il contesto contiene le decisioni precedenti su "{asset}" con azione, prezzo, motivazione ed esito'))
def memory_in_context(memory_cycles: MemoryCycles, asset: str) -> None:
    [entry] = entries_of(memory_cycles.received("alfa"), asset)
    assert_the_opening_with_its_outcome(entry)
    system = memory_cycles.cycles.system_text()
    assert f"{MEMORY_HEADING}\n{asset}:\n- {entry.text}" in system
    assert "apri long, prezzo 95000, PnL realizzato 40: rottura della resistenza" in entry.text


@then("il contesto non contiene decisioni precedenti")
def no_memory_in_context(memory_cycles: MemoryCycles) -> None:
    assert memory_cycles.received("alfa") is None
    system = memory_cycles.cycles.system_text()
    assert MEMORY_HEADING not in system
    assert OPENING_REASONING not in system


@then(quoted('il contesto contiene solo le {count} decisioni più recenti su "{asset}"'))
def only_the_most_recent(memory_cycles: MemoryCycles, count: str, asset: str) -> None:
    entries = entries_of(memory_cycles.received("alfa"), asset)
    assert [entry.reasoning for entry in entries] == [f"stop di {day} giorni fa" for day in range(1, int(count) + 1)]
    system = memory_cycles.cycles.system_text()
    assert all(f"- {entry.text}" in system for entry in entries)
    assert "stop di 3 giorni fa" not in system
    assert "giorni fa" not in system.replace("stop di 1 giorni fa", "").replace("stop di 2 giorni fa", "")


@then("la decisione di non agire non è nella memoria")
def hold_not_remembered(memory_cycles: MemoryCycles) -> None:
    [entry] = entries_of(memory_cycles.received("alfa"), "BTC")
    assert entry.action is DecisionAction.OPEN
    assert "mercato laterale" not in memory_cycles.cycles.system_text()


@then(quoted('la memoria di "{flow}" non contiene le decisioni di "{other}"'))
def other_flow_not_remembered(memory_cycles: MemoryCycles, flow: str, other: str) -> None:
    memory = memory_cycles.received(flow)
    assert memory is not None
    assert all(not asset.entries for asset in memory)
    assert f"chiusura di {other}" not in memory_cycles.cycles.system_text()


@then(quoted("la memoria del flusso è non attiva, con {decisions} decisioni e {days} giorni"))
def memory_default(memory_cycles: MemoryCycles, decisions: str, days: str) -> None:
    assert memory_cycles.created is not None
    assert memory_cycles.created.configuration.memory == FlowMemory(
        active=False, decisions=int(decisions), days=int(days)
    )


@then(
    quoted(
        'vede per "{asset}" le decisioni che l\'agente riceverà al prossimo ciclo, con azione, prezzo, motivazione ed '
        "esito"
    )
)
def memory_read(memory_cycles: MemoryCycles, asset: str) -> None:
    [entry] = entries_of(memory_cycles.remembered, asset)
    assert_the_opening_with_its_outcome(entry)


@then(quoted('"{flow}" ha una nuova versione con la memoria attiva, {decisions} decisioni e {days} giorni'))
def new_version_with_memory(memory_cycles: MemoryCycles, flow: str, decisions: str, days: str) -> None:
    configuration = memory_cycles.cycles.flow(flow).configuration
    assert configuration.version == memory_cycles.version_before + 1
    assert configuration.memory == FlowMemory(active=True, decisions=int(decisions), days=int(days))
