"""Steps shared by the features of the risk check: one flow, its policy, the decisions of the agent, the outcomes.

A scenario module imports them all; pytest-bdd keeps each step as a fixture of this module.
"""

from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.domain.flows.risk_check import RiskPolicy, RiskState
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.risk_outcome import (
    AdjustmentKind,
    ApprovedClose,
    ApprovedOpening,
    BlockedDecision,
    HeldPosition,
    RiskOutcome,
)
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, TradeIntent, TradeSide
from tests.fakes.exchange_limits import FakeExchangeLimitsAdapter

NUMBER = r"(?P<{}>\d+(?:,\d+)?)"
CURRENCY = "USDC"


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def step(text: str) -> parsers.StepParser:
    """A step whose {placeholders} are numbers written with a decimal comma."""
    pattern = text
    for name in ("a", "b", "c", "d"):
        pattern = pattern.replace("{" + name + "}", NUMBER.format(name))
    return parsers.re(f"^{pattern}$")


class RiskBench:
    """The flow under check and the outcome of its decisions."""

    def __init__(self) -> None:
        self.capital = Decimal(1000)
        self.liquidity = Decimal(1000)
        self.realized = Decimal(0)
        self.open_assets: set[str] = set()
        self.max_leverage = 50
        self.margin_percent: Decimal | None = None
        self.value_percent: Decimal | None = None
        self.bring_to_minimum = False
        self.exchange = FakeExchangeLimitsAdapter()
        self.intents: list[TradeIntent] = []
        self.outcomes: tuple[RiskOutcome, ...] = ()

    @property
    def funds(self) -> Decimal:
        return self.capital + self.realized

    def check(self) -> None:
        exposure_set = self.margin_percent is not None or self.value_percent is not None
        margin_percent = self.margin_percent if exposure_set else Decimal(100)
        limits = RiskLimits(self.max_leverage, margin_percent, self.value_percent)
        state = RiskState(CURRENCY, self.funds, self.liquidity, frozenset(self.open_assets))
        command = CheckRiskCommand(tuple(self.intents), RiskPolicy(limits, self.bring_to_minimum), state)
        self.outcomes = CheckRiskUseCase(self.exchange).execute(command)

    def open_with_value(self, asset: str, value: Decimal) -> None:
        self.intents.append(OpenIntent(asset, TradeSide.LONG, value / self.funds, 1))

    def outcome_of(self, asset: str) -> RiskOutcome:
        return next(outcome for outcome in self.outcomes if outcome.asset == asset)

    def opening(self, asset: str = "BTC") -> ApprovedOpening:
        outcome = self.outcome_of(asset)
        assert isinstance(outcome, ApprovedOpening), outcome
        return outcome


@pytest.fixture
def bench() -> RiskBench:
    return RiskBench()


@given(step(r'che "anna" ha il flusso "alfa" con capitale allocato {a} USDC e liquidità disponibile {b} USDC'))
def flow_with_capital(bench: RiskBench, a: str, b: str) -> None:
    bench.capital, bench.liquidity = amount(a), amount(b)


@given(step(r'che "anna" ha il flusso "alfa" con leva massima {a} e capitale allocato {b} USDC'))
def flow_with_leverage(bench: RiskBench, a: str, b: str) -> None:
    bench.max_leverage, bench.capital = int(a), amount(b)


@given(
    step(
        r'che "anna" ha il flusso "alfa" con asset "BTC, ETH", capitale allocato {a} USDC'
        r" e liquidità disponibile {b} USDC"
    )
)
def flow_with_assets(bench: RiskBench, a: str, b: str) -> None:
    bench.capital, bench.liquidity = amount(a), amount(b)


@given(
    step(
        r'che "anna" ha il flusso "alfa" con capitale allocato {a} USDC, esposizione massima del valore {b}%'
        r" e liquidità disponibile {c} USDC"
    )
)
def flow_with_value_exposure(bench: RiskBench, a: str, b: str, c: str) -> None:
    bench.capital, bench.value_percent, bench.liquidity = amount(a), amount(b), amount(c)


@given(step(r'che il flusso "alfa" ha esposizione massima del margine {a}% e nessun limite sul valore'))
def margin_limit_only(bench: RiskBench, a: str) -> None:
    bench.margin_percent, bench.value_percent = amount(a), None


@given(step(r'che il flusso "alfa" ha esposizione massima del valore {a}% e nessun limite sul margine'))
def value_limit_only(bench: RiskBench, a: str) -> None:
    bench.margin_percent, bench.value_percent = None, amount(a)


@given(step(r'che il flusso "alfa" ha esposizione massima del margine {a}% e del valore {b}%'))
def both_limits(bench: RiskBench, a: str, b: str) -> None:
    bench.margin_percent, bench.value_percent = amount(a), amount(b)


@given(step(r'che il flusso "alfa" ha esposizione massima del margine {a}%'))
def margin_limit(bench: RiskBench, a: str) -> None:
    bench.margin_percent = amount(a)


@given(
    parsers.re(
        r'^che il flusso "alfa" ha (?P<outcome>perso|guadagnato) (?P<value>\d+(?:,\d+)?) USDC in posizioni chiuse$'
    )
)
def closed_result(bench: RiskBench, outcome: str, value: str) -> None:
    """A closed result moves both the money of the flow and its liquidity (R1.5.1)."""
    realized = amount(value) if outcome == "guadagnato" else -amount(value)
    bench.realized += realized
    bench.liquidity += realized


@given(step(r'che il flusso "alfa" ha leva massima {a}'))
def flow_leverage(bench: RiskBench, a: str) -> None:
    bench.max_leverage = int(a)


@given(step(r'che l\'exchange ammette per "BTC" una leva massima di {a}'))
def exchange_leverage(bench: RiskBench, a: str) -> None:
    bench.exchange.set("BTC", max_leverage=int(a))


@given(step(r'che l\'exchange ammette per "BTC" un valore minimo di apertura di {a} USDC'))
def exchange_minimum(bench: RiskBench, a: str) -> None:
    bench.exchange.set("BTC", min_order_value=amount(a))


@given(parsers.re(r'^che il flusso "alfa" ha l\'opzione "porta al minimo" attivata$'))
def bring_to_minimum(bench: RiskBench) -> None:
    bench.bring_to_minimum = True


@given(step(r'che il flusso "alfa" ha l\'opzione "porta al minimo" attivata ed esposizione massima del valore {a}%'))
def bring_to_minimum_with_value_limit(bench: RiskBench, a: str) -> None:
    bench.bring_to_minimum, bench.value_percent = True, amount(a)


@given(parsers.re(r'^che il flusso "alfa" ha una posizione long aperta su "(?P<asset>[A-Z]+)"$'))
def open_position(bench: RiskBench, asset: str) -> None:
    bench.open_assets.add(asset)


@given(
    parsers.re(
        r'^che l\'agente decide di aprire (?P<side>long|short) su "(?P<asset>[A-Z]+)"'
        r" con quota (?P<fraction>\d+(?:,\d+)?) e leva (?P<leverage>\d+)$"
    )
)
def agent_opens(bench: RiskBench, side: str, asset: str, fraction: str, leverage: str) -> None:
    bench.intents.append(OpenIntent(asset, TradeSide(side), amount(fraction), int(leverage)))


@given(parsers.re(r'^che l\'agente decide di aprire (?P<side>long|short) su "(?P<asset>[A-Z]+)"$'))
def agent_opens_small(bench: RiskBench, side: str, asset: str) -> None:
    bench.intents.append(OpenIntent(asset, TradeSide(side), Decimal("0.01"), 1))


@given(
    parsers.re(
        r'^che l\'agente decide di aprire long su "(?P<asset>[A-Z]+)" con un margine di (?P<margin>\d+) USDC'
        r" dopo le riduzioni del rischio$"
    )
)
def agent_opens_margin(bench: RiskBench, asset: str, margin: str) -> None:
    bench.open_with_value(asset, amount(margin))


@given(parsers.re(r'^che l\'agente decide un\'apertura su "(?P<asset>[A-Z]+)" di valore (?P<value>\d+) USDC$'))
def agent_opens_value(bench: RiskBench, asset: str, value: str) -> None:
    bench.open_with_value(asset, amount(value))


@given(parsers.re(r'^che l\'agente decide di chiudere su "(?P<asset>[A-Z]+)"$'))
def agent_closes(bench: RiskBench, asset: str) -> None:
    bench.intents.append(CloseIntent(asset))


@given(
    parsers.re(r'^che l\'agente decide di aprire short su "(?P<opened>[A-Z]+)" e di mantenere su "(?P<held>[A-Z]+)"$')
)
def agent_opens_and_holds(bench: RiskBench, opened: str, held: str) -> None:
    bench.intents.extend((OpenIntent(opened, TradeSide.SHORT, Decimal("0.01"), 1), HoldIntent(held)))


@when(parsers.re(r"^il rischio controlla (?:la decisione|le decisioni)$"))
def risk_checks(bench: RiskBench) -> None:
    bench.check()


@then(step(r"l'apertura eseguita impegna {a} USDC di margine con leva {b}"))
def opening_margin(bench: RiskBench, a: str, b: str) -> None:
    opening = bench.opening()
    assert (opening.margin, opening.leverage) == (amount(a), int(b))


@then(step(r"l'apertura eseguita ha valore {a} USDC con leva {b}"))
def opening_value(bench: RiskBench, a: str, b: str) -> None:
    opening = bench.opening()
    assert (opening.value, opening.leverage) == (amount(a), int(b))


@then(step(r"l'apertura eseguita ha leva {a}"))
def opening_leverage(bench: RiskBench, a: str) -> None:
    assert bench.opening().leverage == int(a)


@then(parsers.re(r'^l\'apertura eseguita su "(?P<asset>[A-Z]+)" ha valore (?P<value>\d+) USDC$'))
def opening_value_of(bench: RiskBench, asset: str, value: str) -> None:
    assert bench.opening(asset).value == amount(value)


@then(
    parsers.re(
        r"^il ciclo registra (?:la riduzione|l'aumento) (?:(?P<leverage>della leva) )?"
        r"da (?P<before>\d+) a (?P<after>\d+)"
        r'(?: USDC(?: di (?P<kind>margine|valore))?)? con il motivo "(?P<reason>[^"]+)"$'
    )
)
def adjustment_recorded(
    bench: RiskBench, *, leverage: str | None, before: str, after: str, kind: str | None, reason: str
) -> None:
    expected_kind = AdjustmentKind.LEVERAGE if leverage else AdjustmentKind(kind or "valore")
    recorded = [(item.kind, item.before, item.after, item.reason) for item in bench.opening().adjustments]
    assert (expected_kind, amount(before), amount(after), reason) in recorded


@then(parsers.re(r"^il ciclo non registra riduzioni$"))
def no_adjustment(bench: RiskBench) -> None:
    assert bench.opening().adjustments == ()


@then(parsers.re(r'^la decisione su "(?P<asset>[A-Z]+)" è bloccata con il motivo "(?P<reason>[^"]+)"$'))
def blocked_with_reason(bench: RiskBench, asset: str, reason: str) -> None:
    assert bench.outcome_of(asset) == BlockedDecision(asset, reason)


@then(parsers.re(r'^la decisione su "(?P<asset>[A-Z]+)" è bloccata$'))
def blocked(bench: RiskBench, asset: str) -> None:
    assert isinstance(bench.outcome_of(asset), BlockedDecision)


@then(parsers.re(r'^il ciclo non invia ordini su "(?P<asset>[A-Z]+)"$'))
def no_order(bench: RiskBench, asset: str) -> None:
    """Only an approved outcome becomes an order (R1.5.5): none for the asset means no order on it."""
    assert not any(
        isinstance(outcome, ApprovedOpening | ApprovedClose) and outcome.asset == asset for outcome in bench.outcomes
    )


@then(parsers.re(r'^la decisione su "(?P<asset>[A-Z]+)" è registrata come mantieni$'))
def held(bench: RiskBench, asset: str) -> None:
    assert bench.outcome_of(asset) == HeldPosition(asset)
