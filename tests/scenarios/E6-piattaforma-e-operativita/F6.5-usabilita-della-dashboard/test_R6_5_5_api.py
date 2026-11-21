"""R6.5.5: the history of the decisions of a flow, read on the use cases of the flows context (ADR
storico-delle-decisioni-nell-api). playwright-bdd runs the same scenarios on the tab Decisioni of the dashboard (ADR
scheda-decisioni-nella-pagina-del-flusso).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.list_decisions import ListDecisionsCommand
from autotrading.application.flows.read_cycle import ReadCycleCommand
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.decision_page import DecisionPage
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.recorded_decision import DatedDecision, DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import StatisticsPeriod
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.flows import a_flow
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios(
    "E6-piattaforma-e-operativita/F6.5-usabilita-della-dashboard/R6.5.5-storico-delle-decisioni/api/R6.5.5-storico-delle-decisioni.feature"
)

# The periods of the menu of the page, by the words the user chooses (R6.4.3).
PERIODS = {"Tutta la vita": "all", "7 giorni": "7d", "30 giorni": "30d"}
DAYS = 7
# A cycle older than the week, so the period of 7 days has a decision to leave out.
OLDER_DAYS = 10
REASONING = (
    "Il prezzo ha rotto la resistenza con volumi in aumento e il sentiment resta positivo: la decisione segue il "
    "trend del giorno con leva contenuta e uno stop sotto il minimo della giornata."
)
# What the agent decided each day on BTC and ETH, from today back: every action and direction somewhere.
BTC_DAYS = (
    (DecisionAction.OPEN, TradeSide.LONG),
    (DecisionAction.HOLD, None),
    (DecisionAction.CLOSE, None),
    (DecisionAction.OPEN, TradeSide.SHORT),
    (DecisionAction.HOLD, None),
    (DecisionAction.UPDATE, None),
    (DecisionAction.OPEN, TradeSide.LONG),
)
ETH_DAYS = (
    (DecisionAction.HOLD, None),
    (DecisionAction.OPEN, TradeSide.LONG),
    (DecisionAction.HOLD, None),
    (DecisionAction.CLOSE, None),
    (DecisionAction.OPEN, TradeSide.SHORT),
    (DecisionAction.HOLD, None),
    (DecisionAction.HOLD, None),
)


def a_decision(asset: str, action: DecisionAction, direction: TradeSide | None, confidence: int) -> RecordedDecision:
    return RecordedDecision(asset, action, direction, confidence, REASONING)


@dataclass
class DecisionHistory:
    platform: Platform = field(default_factory=Platform)
    flows: dict[str, Flow] = field(default_factory=dict)
    recorded: list[CycleRecord] = field(default_factory=list)
    user: str = ""
    flow_name: str = ""
    seen: DecisionPage | None = None
    chosen: DatedDecision | None = None
    opened: CycleRecord | None = None

    def flow_of(self, user: str, name: str) -> Flow:
        if name not in self.flows:
            flow = a_flow(self.platform.tenant_of(user), name=name)
            self.platform.flows.flows.append(flow)
            self.flows[name] = flow
        return self.flows[name]

    def record(self, flow: Flow, planned_at: datetime, *decisions: RecordedDecision) -> None:
        cycle = CycleRecord(flow.id.value, planned_at, CycleOutcome.COMPLETED, decisions=decisions)
        self.platform.cycles.record(cycle)
        self.recorded.append(cycle)

    def open_history(self, criteria: DecisionFilter | None = None, period: str = "all") -> None:
        flow = self.flows[self.flow_name]
        command = ListDecisionsCommand(
            flow.id.value, criteria=criteria or DecisionFilter(), period=StatisticsPeriod.named(period)
        )
        self.seen = self.platform.use_cases_of(self.user).list_decisions.execute(command)

    def shown(self) -> tuple[DatedDecision, ...]:
        assert self.seen is not None, "nessuno storico aperto"
        return self.seen.decisions


@pytest.fixture
def history() -> DecisionHistory:
    return DecisionHistory()


# Given


@given(quoted('che "{user}" ha il flusso "{flow}" con cicli conclusi negli ultimi 7 giorni su BTC ed ETH'))
def flow_with_completed_cycles(history: DecisionHistory, user: str, flow: str) -> None:
    owned = history.flow_of(user, flow)
    latest = history.platform.now.replace(second=0, microsecond=0) - timedelta(hours=1)
    for day, ((btc_action, btc_side), (eth_action, eth_side)) in enumerate(zip(BTC_DAYS, ETH_DAYS, strict=True)):
        history.record(
            owned,
            latest - timedelta(days=day),
            a_decision("BTC", btc_action, btc_side, 60 + day),
            a_decision("ETH", eth_action, eth_side, 50 + day),
        )
    history.record(
        owned,
        latest - timedelta(days=OLDER_DAYS),
        a_decision("BTC", DecisionAction.OPEN, TradeSide.LONG, 80),
        a_decision("ETH", DecisionAction.HOLD, None, 30),
    )
    history.user, history.flow_name = user, flow


# When


@when(quoted('"{user}" apre lo storico delle decisioni del flusso "{flow}"'))
def open_history(history: DecisionHistory, user: str, flow: str) -> None:
    history.user, history.flow_name = user, flow
    history.open_history()


@when(quoted('"{user}" filtra lo storico per asset "{asset}" e azione "{action}"'))
def filter_history(history: DecisionHistory, user: str, asset: str, action: str) -> None:
    history.user = user
    history.open_history(DecisionFilter.named(asset=asset, action=action))


@when(quoted('"{user}" sceglie il periodo "{period}"'))
def choose_period(history: DecisionHistory, user: str, period: str) -> None:
    history.user = user
    history.open_history(period=PERIODS[period])


@when(quoted('"{user}" sceglie una riga dello storico'))
def choose_row(history: DecisionHistory, user: str) -> None:
    history.user = user
    history.open_history()
    # A row in the middle of the list: neither the first nor the last cycle.
    history.chosen = history.shown()[3]
    flow = history.flows[history.flow_name]
    command = ReadCycleCommand(flow.id.value, history.chosen.planned_at)
    history.opened = history.platform.use_cases_of(user).read_cycle.execute(command)


# Then


@then("vede una riga per ciclo e asset con istante, asset, azione, direzione, confidenza e ragionamento accorciato")
def one_row_per_cycle_and_asset(history: DecisionHistory) -> None:
    shown = history.shown()
    expected = {(cycle.planned_at, decision.asset) for cycle in history.recorded for decision in cycle.decisions}
    assert sorted((entry.planned_at, entry.decision.asset) for entry in shown) == sorted(expected)
    recorded = {
        (cycle.planned_at, decision.asset): decision for cycle in history.recorded for decision in cycle.decisions
    }
    # Each row carries the whole decision: the dashboard shortens the reasoning, the detail of the cycle shows it all.
    assert all(entry.decision == recorded[entry.planned_at, entry.decision.asset] for entry in shown)
    assert {entry.decision.direction for entry in shown if entry.decision.action is DecisionAction.OPEN} == {
        TradeSide.LONG,
        TradeSide.SHORT,
    }
    assert all(entry.decision.confidence is not None for entry in shown)
    assert all(entry.decision.reasoning == REASONING for entry in shown)


@then("le più recenti in alto")
def newest_first(history: DecisionHistory) -> None:
    instants = [entry.planned_at for entry in history.shown()]
    assert instants == sorted(instants, reverse=True)
    assert instants[0] == max(cycle.planned_at for cycle in history.recorded)


@then(quoted("vede solo le decisioni di aprire su {asset}"))
def only_openings_on(history: DecisionHistory, asset: str) -> None:
    shown = history.shown()
    expected = [
        (cycle.planned_at, decision)
        for cycle in history.recorded
        for decision in cycle.decisions
        if decision.asset == asset and decision.action is DecisionAction.OPEN
    ]
    assert [(entry.planned_at, entry.decision) for entry in shown] == sorted(expected, key=lambda each: each[0])[::-1]
    assert len(shown) == len(expected) > 0


@then("lo storico mostra solo le decisioni degli ultimi 7 giorni")
def only_last_days(history: DecisionHistory) -> None:
    shown = history.shown()
    since = history.platform.now - timedelta(days=DAYS)
    in_week = [decision for cycle in history.recorded if cycle.planned_at >= since for decision in cycle.decisions]
    assert all(entry.planned_at >= since for entry in shown)
    assert len(shown) == len(in_week) == len(BTC_DAYS) * 2


@then("apre il dettaglio del ciclo di quella decisione")
def opens_cycle_of_decision(history: DecisionHistory) -> None:
    assert history.chosen is not None
    assert history.opened is not None
    assert history.opened.planned_at == history.chosen.planned_at
    assert history.chosen.decision in history.opened.decisions
