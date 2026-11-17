"""The overall exposure of a flow in the risk check of its cycles, on the cycles the worker runs (R3.2.1).

ADR-esposizione-complessiva-nel-controllo-del-rischio: the overall limits are a step of the risk check of the cycle,
after the limit per operation, and the openings of one cycle consume the residual in their order.
"""

import json
import re
from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.orders.market import Market
from tests.support.activity import a_position, an_activity
from tests.support.decision_steps import answer, opening
from tests.support.flow_cycle_steps import names_of, position
from tests.support.flow_cycles import FlowCycles

scenarios("E3-rischio-capitale-e-qualita/F3.2-limiti-di-rischio/R3.2.1-esposizione-complessiva-massima.feature")

NUMBER = r"(?P<{}>\d+(?:,\d+)?)"
# The leverage of the flow and the limit per operation leave room to every opening of the scenarios: only the overall
# limits under test reduce them.
MAX_LEVERAGE = 10
OPERATION_LIMIT = Decimal(100)
REDUCTION = re.compile(
    r"^apertura (?P<asset>\w+) ridotta da (?P<before>[\d,]+) a (?P<after>[\d,]+) USDC "
    r"di (?P<kind>margine|valore): (?P<reason>.+)$"
)


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def step(text: str) -> parsers.StepParser:
    """A step whose {a}, {b}, {c} are numbers written with a decimal comma."""
    pattern = text
    for name in ("a", "b", "c"):
        pattern = pattern.replace("{" + name + "}", NUMBER.format(name))
    return parsers.re(f"^{pattern}$")


class OverallExposure:
    """The flow under the overall limits, the decisions its agent takes and the user's refused changes."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles
        self.funds = Decimal(0)
        self.refusals: list[AutotradingError] = []

    def limit(self, margin: Decimal | None = None, value: Decimal | None = None) -> None:
        self.flow_cycles.reconfigure(
            "alfa",
            lambda configuration: replace(
                configuration,
                risk_limits=replace(
                    configuration.risk_limits,
                    max_total_margin_exposure_percent=margin,
                    max_total_value_exposure_percent=value,
                ),
            ),
        )

    def hold(self, asset: str, *, leverage: int, margin: Decimal, value: Decimal) -> None:
        """A position of the flow as the exchange shows it: its margin, and its value at the mark price."""
        cycles = self.flow_cycles
        mark_price = Decimal(100)
        size = value / mark_price
        cycles.platform.hyperliquid.open_position(cycles.credentials_of("alfa"), position(asset, size=size))
        address = cycles.credentials_of("alfa").value("account_address")
        held = a_position(asset, margin=margin, size=size, leverage=leverage, mark_price=mark_price)
        cycles.platform.activity_reader.activities[address] = an_activity(positions=(held,))
        cycles.platform.ledger.expect(cycles.flow("alfa").id, asset, size)

    def decide(self, *openings: tuple[str, int, Decimal]) -> None:
        """The agent opens long each asset with the margin and the leverage given, then the cycle runs."""
        answer(
            self.flow_cycles,
            *(opening(asset, float(margin / self.funds), leverage) for asset, leverage, margin in openings),
        )
        self.flow_cycles.run("alfa")

    def outcomes(self) -> list[dict[str, object]]:
        document = self.flow_cycles.last_record("alfa").document(CycleStep.RISK_CHECK)
        assert document is not None
        outcomes = document["esiti"]
        assert isinstance(outcomes, list)
        return outcomes

    def outcome_of(self, asset: str) -> dict[str, object]:
        [outcome] = [outcome for outcome in self.outcomes() if outcome["asset"] == asset]
        return outcome

    def opened(self, asset: str) -> tuple[Decimal, Decimal]:
        """Margin and value of the opening approved on the asset, which the cycle sends to the exchange."""
        outcome = self.outcome_of(asset)
        assert outcome["tipo"] == "ApprovedOpening", outcome
        assert asset in {order.coin for order in self.flow_cycles.platform.order_exchange.sent}
        value = Decimal(str(outcome["value"]))
        return value / Decimal(str(outcome["leverage"])), value


@pytest.fixture
def flow_cycles() -> FlowCycles:
    cycles = FlowCycles()
    cycles.platform.order_exchange.markets["SOL"] = Market(
        "SOL", max_leverage=20, size_decimals=2, mid_price=Decimal(200), min_order_value=Decimal(10)
    )
    return cycles


@pytest.fixture
def exposure(flow_cycles: FlowCycles) -> OverallExposure:
    return OverallExposure(flow_cycles)


# Given


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "alfa" attivo con asset (?P<assets>.+) '
        r"e soldi del flusso per (?P<funds>\d+) USDC$"
    )
)
def flow_with_funds(exposure: OverallExposure, user: str, assets: str, funds: str) -> None:
    listed = names_of(assets.replace('"', "").replace(" e ", ", "))
    exposure.flow_cycles.add_flow(user, "alfa", assets=listed)
    exposure.funds = amount(funds)
    exposure.flow_cycles.reconfigure(
        "alfa",
        lambda configuration: replace(
            configuration,
            allocated_capital=exposure.funds,
            risk_limits=RiskLimits(MAX_LEVERAGE, OPERATION_LIMIT),
        ),
    )


@given(step(r'che "alfa" ha esposizione complessiva massima del margine {a}%'))
def margin_limit(exposure: OverallExposure, a: str) -> None:
    exposure.limit(margin=amount(a))


@given(step(r'che "alfa" ha esposizione complessiva massima del valore {a}%'))
def value_limit(exposure: OverallExposure, a: str) -> None:
    exposure.limit(value=amount(a))


@given(step(r'che "alfa" ha esposizione complessiva massima del margine {a}% e del valore {b}%'))
def both_limits(exposure: OverallExposure, a: str, b: str) -> None:
    exposure.limit(margin=amount(a), value=amount(b))


@given(step(r'che "alfa" ha esposizione complessiva massima del margine {a}% e nessuna posizione aperta'))
def margin_limit_without_positions(exposure: OverallExposure, a: str) -> None:
    exposure.limit(margin=amount(a))


@given('che "alfa" non ha limiti di esposizione complessiva')
def no_overall_limits(exposure: OverallExposure) -> None:
    limits = exposure.flow_cycles.flow("alfa").configuration.risk_limits
    assert (limits.max_total_margin_exposure_percent, limits.max_total_value_exposure_percent) == (None, None)


@given(step(r'che "alfa" ha una posizione su "(?P<asset>\w+)" con margine {a} USDC'))
def position_with_margin(exposure: OverallExposure, asset: str, a: str) -> None:
    exposure.hold(asset, leverage=1, margin=amount(a), value=amount(a))


@given(step(r'che "alfa" ha una posizione su "(?P<asset>\w+)" di valore {a} USDC'))
def position_with_value(exposure: OverallExposure, asset: str, a: str) -> None:
    exposure.hold(asset, leverage=1, margin=amount(a), value=amount(a))


@given(step(r'che "alfa" ha una posizione su "(?P<asset>\w+)" con leva {a}, margine {b} USDC e valore {c} USDC'))
def position_with_leverage(exposure: OverallExposure, asset: str, a: str, b: str, c: str) -> None:
    exposure.hold(asset, leverage=int(a), margin=amount(b), value=amount(c))


# When


@when(step(r'l\'agente di "alfa" decide di aprire long su "(?P<asset>\w+)" con margine {a} USDC'))
def opens_with_margin(exposure: OverallExposure, asset: str, a: str) -> None:
    exposure.decide((asset, 1, amount(a)))


@when(step(r'l\'agente di "alfa" decide di aprire long su "(?P<asset>\w+)" di valore {a} USDC'))
def opens_with_value(exposure: OverallExposure, asset: str, a: str) -> None:
    exposure.decide((asset, 1, amount(a)))


@when(
    step(
        r'l\'agente di "alfa" decide di aprire long su "(?P<asset>\w+)" con leva {a}, margine {b} USDC '
        r"e valore {c} USDC"
    )
)
def opens_with_leverage(exposure: OverallExposure, asset: str, a: str, b: str, c: str) -> None:
    assert amount(b) * int(a) == amount(c)
    exposure.decide((asset, int(a), amount(b)))


@when(
    step(
        r'l\'agente di "alfa" decide nello stesso ciclo di aprire "(?P<first>\w+)" con margine {a} USDC '
        r'e "(?P<second>\w+)" con margine {b} USDC'
    )
)
def opens_two(exposure: OverallExposure, first: str, a: str, second: str, b: str) -> None:
    exposure.decide((first, 1, amount(a)), (second, 1, amount(b)))


@when(step(r'"(?P<user>[^"]+)" imposta l\'esposizione complessiva massima del margine di "alfa" a {a}%'))
def set_margin_limit(exposure: OverallExposure, user: str, a: str) -> None:
    command = ModifyFlowCommand(exposure.flow_cycles.flow("alfa").id, max_total_margin_exposure_percent=amount(a))
    try:
        exposure.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
    except AutotradingError as error:
        exposure.refusals.append(error)


# Then


@then(step(r'"alfa" apre la posizione su "(?P<asset>\w+)" con margine {a} USDC'))
def opened_with_margin(exposure: OverallExposure, asset: str, a: str) -> None:
    margin, _ = exposure.opened(asset)
    assert margin == amount(a)


@then(step(r'"alfa" apre la posizione su "(?P<asset>\w+)" di valore {a} USDC'))
def opened_with_value(exposure: OverallExposure, asset: str, a: str) -> None:
    _, value = exposure.opened(asset)
    assert value == amount(a)


@then(step(r'"alfa" apre la posizione su "(?P<asset>\w+)" con margine {a} USDC e valore {b} USDC'))
def opened_with_margin_and_value(exposure: OverallExposure, asset: str, a: str, b: str) -> None:
    assert exposure.opened(asset) == (amount(a), amount(b))


@then(parsers.re(r'^"alfa" non apre la posizione su "(?P<asset>\w+)"$'))
def not_opened(exposure: OverallExposure, asset: str) -> None:
    assert exposure.outcome_of(asset)["tipo"] == "BlockedDecision"
    assert asset not in {order.coin for order in exposure.flow_cycles.platform.order_exchange.sent}


@then(parsers.re(r'^il ciclo di "alfa" registra "(?P<text>[^"]+)"$'))
def cycle_records(exposure: OverallExposure, text: str) -> None:
    reduction = REDUCTION.match(text)
    if reduction is None:
        assert text in [outcome.get("reason") for outcome in exposure.outcomes()], json.dumps(exposure.outcomes())
        return
    adjustments = exposure.outcome_of(reduction["asset"])["adjustments"]
    assert isinstance(adjustments, list)
    recorded = [(item["kind"], amount(item["before"]), amount(item["after"]), item["reason"]) for item in adjustments]
    expected = (
        f"{reduction['kind']} complessivo",
        amount(reduction["before"]),
        amount(reduction["after"]),
        reduction["reason"],
    )
    assert expected in recorded, recorded


@then(parsers.re(r'^la modifica viene rifiutata con "(?P<reason>[^"]+)"$'))
def modification_refused(exposure: OverallExposure, reason: str) -> None:
    assert [str(error) for error in exposure.refusals] == [reason]
    configuration = exposure.flow_cycles.flow("alfa").configuration
    assert (configuration.version, configuration.risk_limits.max_total_margin_exposure_percent) == (1, None)
