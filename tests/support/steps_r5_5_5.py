"""R5.5.5: the flows of an account together hold on each side at most a percent of its balance, and a flow may show its
agent the exposure of the other flows of the account; run as the worker, the API and the MCP server compose them (ADR
esposizione-massima-per-direzione-del-conto, ADR controllo-dell-esposizione-del-conto-nel-rischio, ADR
esposizione-degli-altri-flussi-nel-contesto-dell-agente).

The positions of the other flows stand on the exchange at the price `OTHERS_PRICE`, so that their size gives the value
the step names; the openings of "alfa" have leverage 2 on a capital of 1000, so that their share gives the value.
"""

import json
from dataclasses import dataclass, replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.set_max_direction_exposure import SetMaxDirectionExposureCommand
from autotrading.application.flows.create_flow import CreateFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.activity import an_activity
from tests.support.flow_cycles import FlowCycles
from tests.support.flows import OPENROUTER_MODEL
from tests.support.mcp_session import McpSession, body_of
from tests.support.platform import HYPERLIQUID
from tests.support.steps import quoted
from tests.support.steps_r3_1_2 import NO_DECISIONS, Protection, plan_of
from tests.support.steps_r5_5_3 import StopInForce

USER, ACCOUNT = "anna", "principale"
OTHERS_PRICE = Decimal(100)
ETH_PRICE = "2000"
CAPITAL = Decimal(1000)
LEVERAGE = 2
CYCLE_HOUR = "14:00"
NEW_ASSET = "AVAX"
ASSETS_OF = {"alfa": ("ETH",), "beta": ("BTC",), "gamma": ("SOL", "DOGE")}
SIDE_OF = {"long": PositionSide.LONG, "short": PositionSide.SHORT}
STATE_OF = {"accesa": True, "spenta": False}


@dataclass
class AccountExposureSteps:
    """The flows of one account, the cycles that run them, and what the user changed and read."""

    stops: StopInForce
    error: AutotradingError | None = None
    version_before: int = 0
    summary: AccountSummary | None = None
    created: Flow | None = None
    read_flow: dict[str, object] | None = None
    read_accounts: list[dict[str, object]] | None = None

    @property
    def flow_cycles(self) -> FlowCycles:
        return self.stops.flow_cycles

    def account_id(self) -> AccountId:
        return AccountId(self.flow_cycles.account_of(USER, ACCOUNT))

    def ensure_flow(self, flow: str) -> Flow:
        """The flow on the account, active on its assets, added once."""
        if flow not in self.flow_cycles.users:
            assets = ASSETS_OF[flow]
            self.flow_cycles.add_flow(USER, flow, assets=assets, account=ACCOUNT)
            markets = self.flow_cycles.platform.markets[HYPERLIQUID]
            markets.assets = markets.assets | set(assets)
        return self.flow_cycles.flow(flow)

    def limit(self, percent: Decimal | None) -> None:
        """The limit as the account holds it now: a step that names it sets it in the database."""
        accounts = self.flow_cycles.platform.accounts.accounts
        account = self.flow_cycles.platform.account_named(USER, ACCOUNT)
        accounts[accounts.index(account)] = account.with_max_direction_exposure(percent)

    def balance(self, amount: Decimal) -> None:
        self.ensure_flow("alfa")
        credentials = self.flow_cycles.credentials_of("alfa", ACCOUNT)
        self.flow_cycles.platform.hyperliquid.accept(credentials, amount=amount)

    def hold(self, flow: str, side: str, asset: str, value: str) -> None:
        """A position of the flow on the account, as the exchange reads it."""
        self.ensure_flow(flow)
        size = Decimal(value) / OTHERS_PRICE
        position = Position(asset, SIDE_OF[side], size, 1, OTHERS_PRICE, OTHERS_PRICE, Decimal(0), None)
        self.flow_cycles.platform.hyperliquid.open_position(self.flow_cycles.credentials_of(flow, ACCOUNT), position)

    def trading_flow(self) -> None:
        """ "alfa" on ETH with the capital and the limits that let its share give the value of an opening."""
        self.ensure_flow("alfa")
        self.flow_cycles.reconfigure(
            "alfa",
            lambda configuration: replace(
                configuration, allocated_capital=CAPITAL, risk_limits=RiskLimits(10, Decimal(100))
            ),
        )
        self.stops.protection.at_price("ETH", Decimal(ETH_PRICE))
        self.flow_cycles.model.text = NO_DECISIONS

    def decides(self, action: str, side: str | None, value: str) -> None:
        decision = {
            **plan_of(),
            "asset": "ETH",
            "azione": action,
            "direzione": side,
            "quota": float(share_of(value)),
            "leva": LEVERAGE,
            "invalidazione": None,
            "togli_obiettivo": False,
            "confidenza": 70,
            "ragionamento": "la tendenza riprende",
        }
        self.flow_cycles.model.text = json.dumps({"decisioni": [decision]})
        self.flow_cycles.run("alfa", CYCLE_HOUR)
        self.flow_cycles.model.text = NO_DECISIONS

    def address(self) -> str:
        return self.flow_cycles.credentials_of("alfa", ACCOUNT).value("account_address")

    def open_long(self, value: str) -> None:
        """A long of "alfa" opened by its agent, as the exchange then shows it to the worker and to the API."""
        platform, recorded = self.flow_cycles.platform, self.flow_cycles.flow("alfa")
        self.stops.protection.open(
            "alfa", "long", "ETH", {**plan_of(), "quota": float(share_of(value)), "leva": LEVERAGE}
        )
        held = platform.order_exchange.positions[self.address(), "ETH"]
        position = AccountPosition(
            "ETH", TradeSide.LONG, held.size, Decimal(10), Decimal(0), held.leverage, held.entry_price, held.entry_price
        )
        activity = an_activity(positions=(position,))
        platform.activity_reader.activities[self.address()] = activity
        platform.account_activity.activities[recorded.assigned_account_id] = activity
        platform.ledger.expect(recorded.id, "ETH", held.size)

    def outcome(self, step: CycleStep, part: str) -> dict[str, object]:
        document = self.flow_cycles.last_record("alfa").document(step)
        assert document is not None
        outcomes = document[part]
        assert isinstance(outcomes, list)
        [outcome] = [outcome for outcome in outcomes if outcome["asset"] == "ETH"]
        assert isinstance(outcome, dict)
        return outcome

    def exposure_in_context(self) -> object:
        state = self.flow_cycles.context()["stato_del_flusso"]
        assert isinstance(state, dict)
        return state.get("esposizione_degli_altri_flussi")

    def set_limit(self, user: str, percent: Decimal | None) -> None:
        use_cases = self.flow_cycles.platform.use_cases_of(user)
        try:
            use_cases.set_max_direction_exposure.execute(SetMaxDirectionExposureCommand(self.account_id(), percent))
        except AutotradingError as error:
            self.error = error
            return
        self.read_account(user)

    def read_account(self, user: str) -> None:
        use_cases = self.flow_cycles.platform.use_cases_of(user)
        self.summary = use_cases.get_account.execute(GetAccountCommand(self.account_id()))

    def turn_on(self, user: str, flow: str) -> None:
        recorded = self.ensure_flow(flow)
        self.version_before = recorded.configuration.version
        command = ModifyFlowCommand(recorded.id, account_exposure_for_agent=True)
        self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)

    def mcp(self) -> McpSession:
        return McpSession(self.flow_cycles.platform)


def share_of(value: str) -> Decimal:
    """The share of the capital of "alfa" that, at its leverage, opens a position of that value."""
    return Decimal(value) / (CAPITAL * LEVERAGE)


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def exposure(flow_cycles: FlowCycles) -> AccountExposureSteps:
    return AccountExposureSteps(StopInForce(Protection(flow_cycles)))


# Given


@given(quoted('che "{user}" ha il conto "{account}" con i flussi "alfa", "beta" e "gamma"'))
def account_with_flows(exposure: AccountExposureSteps, user: str, account: str) -> None:
    assert (user, account) == (USER, ACCOUNT)
    for flow in ASSETS_OF:
        exposure.ensure_flow(flow)


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il conto "(?P<account>[^"]+)" con saldo (?P<balance>\d+) USDC ed esposizione '
        r"massima per direzione (?P<percent>\d+)%$"
    )
)
def account_with_limit(exposure: AccountExposureSteps, user: str, account: str, balance: str, percent: str) -> None:
    assert (user, account) == (USER, ACCOUNT)
    exposure.balance(Decimal(balance))
    exposure.limit(Decimal(percent))


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha una posizione (?P<side>long|short) su "(?P<asset>[^"]+)" di valore '
        r"(?P<value>\d+) USDC$"
    )
)
def flow_position(exposure: AccountExposureSteps, flow: str, side: str, asset: str, value: str) -> None:
    exposure.hold(flow, side, asset, value)


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha una posizione (?P<first_side>long|short) su "(?P<first>[^"]+)" di valore '
        r'(?P<first_value>\d+) USDC e una posizione (?P<second_side>long|short) su "(?P<second>[^"]+)" di valore '
        r"(?P<second_value>\d+) USDC$"
    )
)
def flow_positions(  # noqa: PLR0917 - one argument per value of the step
    exposure: AccountExposureSteps,
    flow: str,
    first_side: str,
    first: str,
    first_value: str,
    second_side: str,
    second: str,
    second_value: str,
) -> None:
    exposure.hold(flow, first_side, first, first_value)
    exposure.hold(flow, second_side, second, second_value)


@given(quoted('che il flusso "alfa" è attivo con asset "ETH" e senza posizioni'))
def trading_flow(exposure: AccountExposureSteps) -> None:
    exposure.trading_flow()


@given(quoted('che "alfa" ha «porta al minimo» acceso'))
def brought_to_minimum(exposure: AccountExposureSteps) -> None:
    exposure.flow_cycles.reconfigure("alfa", lambda configuration: replace(configuration, bring_to_minimum=True))


@given(parsers.re(r'^che "alfa" ha una posizione long su "ETH" di valore (?P<value>\d+) USDC$'))
def long_position(exposure: AccountExposureSteps, value: str) -> None:
    exposure.open_long(value)


@given(quoted('che il conto "principale" non ha esposizione massima per direzione'))
@given(quoted('che il conto "principale" esisteva prima del limite di esposizione per direzione'))
def account_without_limit(exposure: AccountExposureSteps) -> None:
    # An account saved before reads the limit as absent (ADR esposizione-massima-per-direzione-del-conto).
    exposure.ensure_flow("alfa")
    exposure.limit(None)


@given(parsers.re(r'^che il conto "principale" ha esposizione massima per direzione (?P<percent>\d+)%$'))
def account_limit(exposure: AccountExposureSteps, percent: str) -> None:
    exposure.ensure_flow("alfa")
    exposure.limit(Decimal(percent))


@given(parsers.re(r'^che "alfa" ha l\'esposizione del conto nel contesto dell\'agente (?P<state>accesa|spenta)$'))
def agent_option(exposure: AccountExposureSteps, state: str) -> None:
    shown = STATE_OF[state]
    exposure.flow_cycles.reconfigure(
        "alfa", lambda configuration: replace(configuration, account_exposure_for_agent=shown)
    )


# When


@when(
    parsers.re(
        r'^l\'agente di "alfa" decide di aprire (?P<side>long|short) su "ETH" per un valore di (?P<value>\d+) USDC$'
    )
)
def agent_opens(exposure: AccountExposureSteps, side: str, value: str) -> None:
    exposure.decides("apri", side, value)


@when(
    parsers.re(r'^l\'agente di "alfa" decide di invertire la posizione su "ETH" con un valore di (?P<value>\d+) USDC$')
)
def agent_reverses(exposure: AccountExposureSteps, value: str) -> None:
    exposure.decides("inverti", None, value)


@when(quoted('parte il ciclo di "alfa"'))
def cycle_starts(exposure: AccountExposureSteps) -> None:
    exposure.flow_cycles.run("alfa", CYCLE_HOUR)


@when(quoted('"{user}" legge il conto "principale"'))
def reads_account(exposure: AccountExposureSteps, user: str) -> None:
    exposure.read_account(user)


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" imposta l\'esposizione massima per direzione del conto "principale" a (?P<percent>\d+)%$'
    )
)
def sets_limit(exposure: AccountExposureSteps, user: str, percent: str) -> None:
    exposure.set_limit(user, Decimal(percent))


@when(quoted('"{user}" toglie l\'esposizione massima per direzione del conto "principale"'))
def removes_limit(exposure: AccountExposureSteps, user: str) -> None:
    exposure.set_limit(user, None)


@when(quoted('"{user}" crea il flusso "{flow}" senza indicare l\'esposizione del conto nel contesto dell\'agente'))
def creates_flow(exposure: AccountExposureSteps, user: str, flow: str) -> None:
    flow_cycles = exposure.flow_cycles
    markets = flow_cycles.platform.markets[HYPERLIQUID]
    markets.assets = markets.assets | {NEW_ASSET}
    command = CreateFlowCommand(
        name=flow,
        account_id=exposure.account_id().value,
        assets=(NEW_ASSET,),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
    )
    exposure.created = flow_cycles.platform.use_cases_of(user).create_flow.execute(command)


@when(quoted('"{user}" accende per "{flow}" l\'esposizione del conto nel contesto dell\'agente'))
def turns_on(exposure: AccountExposureSteps, user: str, flow: str) -> None:
    exposure.turn_on(user, flow)


@when(quoted('il client MCP di "{user}" accende per "{flow}" l\'esposizione del conto nel contesto dell\'agente'))
def mcp_turns_on(exposure: AccountExposureSteps, user: str, flow: str) -> None:
    flow_id = str(exposure.ensure_flow(flow).id.value)
    arguments = {"flow_id": flow_id, "modification": {"account_exposure_for_agent": True}}
    result = exposure.mcp().call_as(user, "modify_flow", arguments)
    assert not result.is_error, body_of(result)
    exposure.read_flow = body_of(exposure.mcp().call_as(user, "get_flow", {"flow_id": flow_id}))


@when(quoted('il client MCP di "{user}" legge i conti'))
def mcp_reads_accounts(exposure: AccountExposureSteps, user: str) -> None:
    result = exposure.mcp().call_as(user, "list_accounts", {})
    assert not result.is_error, body_of(result)
    exposure.read_accounts = body_of(result)["accounts"]


# Then


@then(quoted('la decisione su "ETH" viene bloccata con "{reason}"'))
def decision_blocked(exposure: AccountExposureSteps, reason: str) -> None:
    outcome = exposure.outcome(CycleStep.RISK_CHECK, "esiti")
    assert (outcome["tipo"], outcome["reason"]) == ("BlockedDecision", reason)


@then(quoted('la decisione su "ETH" viene approvata'))
def decision_approved(exposure: AccountExposureSteps) -> None:
    assert exposure.outcome(CycleStep.RISK_CHECK, "esiti")["tipo"] == "ApprovedOpening"


@then(quoted('la posizione long di "alfa" su "ETH" viene chiusa'))
def long_closed(exposure: AccountExposureSteps) -> None:
    assert exposure.outcome(CycleStep.RISK_CHECK, "esiti")["tipo"] == "ApprovedClose"
    [closing] = [order for order in exposure.flow_cycles.platform.order_exchange.sent if order.coin == "ETH"][-1:]
    assert closing.reduce_only


@then(quoted('sull\'exchange non c\'è nessuna posizione di "alfa" su "ETH"'))
def no_position(exposure: AccountExposureSteps) -> None:
    assert exposure.flow_cycles.platform.order_exchange.positions.get((exposure.address(), "ETH")) is None


@then(quoted('lo stato del flusso inviato all\'agente riporta "{text}"'))
def exposure_in_context(exposure: AccountExposureSteps, text: str) -> None:
    assert exposure.exposure_in_context() == text


@then(quoted('lo stato del flusso inviato all\'agente non riporta "{text}"'))
def no_exposure_in_context(exposure: AccountExposureSteps, text: str) -> None:
    assert exposure.exposure_in_context() is None
    assert text not in exposure.flow_cycles.system_text() + json.dumps(exposure.flow_cycles.context())


@then(quoted('il conto "principale" non ha esposizione massima per direzione'))
def no_limit(exposure: AccountExposureSteps) -> None:
    assert exposure.summary is not None
    assert exposure.summary.max_direction_exposure_percent is None


@then(parsers.re(r'^il conto "principale" ha esposizione massima per direzione (?P<percent>\d+)%$'))
def with_limit(exposure: AccountExposureSteps, percent: str) -> None:
    assert exposure.summary is not None
    assert exposure.summary.max_direction_exposure_percent == Decimal(percent)


@then(quoted('la modifica viene rifiutata con "{message}"'))
def refused(exposure: AccountExposureSteps, message: str) -> None:
    assert exposure.error is not None
    assert str(exposure.error) == message
    exposure.read_account(USER)
    assert exposure.summary is not None
    assert exposure.summary.max_direction_exposure_percent is None


@then(quoted("il flusso \"{flow}\" ha l'esposizione del conto nel contesto dell'agente spenta"))
def option_off(exposure: AccountExposureSteps, flow: str) -> None:
    assert exposure.created is not None
    assert exposure.created.name.value == flow
    assert exposure.created.configuration.account_exposure_for_agent is False


@then(
    quoted(
        "\"{flow}\" ha una nuova versione della configurazione con l'esposizione del conto nel contesto dell'agente "
        "accesa"
    )
)
def new_version_with_option(exposure: AccountExposureSteps, flow: str) -> None:
    configuration = exposure.flow_cycles.flow(flow).configuration
    assert configuration.version == exposure.version_before + 1
    assert configuration.account_exposure_for_agent is True


@then(
    quoted(
        "il dettaglio di \"{flow}\" letto dagli strumenti riporta l'esposizione del conto nel contesto dell'agente "
        "accesa"
    )
)
def tools_detail(exposure: AccountExposureSteps, flow: str) -> None:
    assert exposure.read_flow is not None
    assert exposure.read_flow["name"] == flow
    assert exposure.read_flow["account_exposure_for_agent"] is True


@then(parsers.re(r'^il conto "principale" riporta esposizione massima per direzione (?P<percent>\d+)%$'))
def tools_account(exposure: AccountExposureSteps, percent: str) -> None:
    assert exposure.read_accounts is not None
    [account] = [each for each in exposure.read_accounts if each["name"] == ACCOUNT]
    assert account["max_direction_exposure_percent"] == percent
