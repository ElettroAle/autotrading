"""R5.5.2: after a number of consecutive losses on a side, the reopenings of that side stop for a time, counted on each
asset or on the whole flow; run as the worker, the API and the MCP server compose them (ADR
limite-di-perdite-consecutive-del-flusso, ADR controllo-delle-riaperture-dopo-perdite-consecutive).

The closed positions the counting reads are written in the history of the flow as the cycles of the exchange left
them: a step that names a closing at an hour adds it, at that hour of the day of the cycles.
"""

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.create_flow import ConsecutiveLossLimitRequest, CreateFlowCommand
from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit, LossCountScope
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.activity import an_activity
from tests.support.closings import a_closing
from tests.support.flow_cycles import FlowCycles, at
from tests.support.flows import OPENROUTER_MODEL
from tests.support.mcp_session import McpSession, body_of
from tests.support.platform import HYPERLIQUID
from tests.support.steps import quoted
from tests.support.steps_r3_1_2 import NO_DECISIONS, Protection
from tests.support.steps_r5_5_3 import StopInForce

PRICE = "2"
LOSS, PROFIT, EVEN = Decimal(-3), Decimal(4), Decimal(0)
RESULT_OF = {"in utile": PROFIT, "in pari": EVEN}
BLOCKED_HOUR = "14:00"
LIMIT = (
    r"perdite consecutive massime (?P<losses>\d+), finestra (?P<hours>\d+) ore e durata del blocco "
    r"(?P<minutes>\d+) minuti"
)


@dataclass
class ReopeningBlocks:
    """The flow whose closings may stop its reopenings, the cycles that run it, and what the user changed and read."""

    stops: StopInForce
    error: AutotradingError | None = None
    version_before: int = 0
    read: Flow | None = None
    read_flow: dict[str, object] = field(default_factory=dict)
    read_blocks: list[str] = field(default_factory=list)

    @property
    def flow_cycles(self) -> FlowCycles:
        return self.stops.flow_cycles

    def add_flow(self, user: str, flow: str, assets: tuple[str, ...]) -> None:
        """The flow active on the assets, each traded on the exchange at the same price."""
        flow_cycles = self.flow_cycles
        flow_cycles.add_flow(user, flow, assets=assets)
        exchange = flow_cycles.platform.order_exchange
        markets = flow_cycles.platform.markets[HYPERLIQUID]
        markets.assets = markets.assets | set(assets)
        for asset in assets:
            exchange.markets[asset] = replace(exchange.markets["ETH"], coin=asset, size_decimals=1)
            self.stops.protection.at_price(asset, Decimal(PRICE))
        flow_cycles.model.text = NO_DECISIONS

    def ensure_flow(self, user: str, flow: str) -> None:
        """The flow the scenarios of the tools name: active on NEAR, its account read with no position."""
        if flow not in self.flow_cycles.users:
            self.add_flow(user, flow, ("NEAR",))
        account_id = self.flow_cycles.flow(flow).assigned_account_id
        self.flow_cycles.platform.account_activity.activities[account_id] = an_activity()

    def limit(self, flow: str, limit: ConsecutiveLossLimit | None) -> None:
        """The limit as the flow holds it now, without a new version."""
        self.flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, consecutive_loss_limit=limit))

    def limit_of(self, flow: str) -> ConsecutiveLossLimit:
        limit = self.flow_cycles.flow(flow).configuration.consecutive_loss_limit
        assert limit is not None
        return limit

    def closed(self, flow: str, side: str, asset: str, closed_at: datetime, result: Decimal = LOSS) -> None:
        recorded = self.flow_cycles.flow(flow)
        closing = a_closing(
            TradeSide(side), asset, closed_at, result, tenant_id=recorded.tenant_id, flow_id=recorded.id
        )
        self.flow_cycles.platform.closed_positions.positions.append(closing)

    def closed_instead(self, flow: str) -> None:
        """The closings of the background give way to those of the scenario."""
        recorded = self.flow_cycles.flow(flow)
        closed = self.flow_cycles.platform.closed_positions.positions
        closed[:] = [position for position in closed if position.flow_id != recorded.id]

    def decides(self, flow: str, action: str, side: str | None, asset: str, clock: str) -> None:
        decision = {
            "asset": asset,
            "azione": action,
            "direzione": side,
            "quota": 0.1,
            "leva": 2,
            "obiettivo": None,
            "stop": None,
            "invalidazione": None,
            "togli_obiettivo": False,
            "confidenza": 70,
            "ragionamento": "la tendenza riprende",
        }
        self.flow_cycles.model.text = json.dumps({"decisioni": [decision]})
        self.flow_cycles.run(flow, clock)
        self.flow_cycles.model.text = NO_DECISIONS

    def outcome(self, flow: str, step: CycleStep, part: str, asset: str) -> dict[str, object]:
        document = self.flow_cycles.last_record(flow).document(step)
        assert document is not None
        outcomes = document[part]
        assert isinstance(outcomes, list)
        [outcome] = [outcome for outcome in outcomes if outcome["asset"] == asset]
        assert isinstance(outcome, dict)
        return outcome

    def held(self, flow: str, asset: str) -> object:
        return self.flow_cycles.platform.order_exchange.positions.get((self.stops.protection.address(flow), asset))

    def stopped_in_context(self) -> object:
        state = self.flow_cycles.context()["stato_del_flusso"]
        assert isinstance(state, dict)
        return state.get("riaperture_ferme")

    def modify(self, user: str, flow: str, request: ConsecutiveLossLimitRequest) -> None:
        recorded = self.flow_cycles.flow(flow)
        self.version_before = recorded.configuration.version
        try:
            self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(
                ModifyFlowCommand(recorded.id, consecutive_loss_limit=request)
            )
        except AutotradingError as error:
            self.error = error

    def mcp(self) -> McpSession:
        return McpSession(self.flow_cycles.platform)


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def blocks(flow_cycles: FlowCycles) -> ReopeningBlocks:
    return ReopeningBlocks(StopInForce(Protection(flow_cycles)))


# Given


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "(?P<flow>[^"]+)" attivo con asset "(?P<first>[^"]+)" e '
        rf'"(?P<second>[^"]+)", {LIMIT}$'
    )
)
def limited_flow(  # noqa: PLR0917 - one argument per value of the step
    blocks: ReopeningBlocks, user: str, flow: str, first: str, second: str, losses: str, hours: str, minutes: str
) -> None:
    blocks.add_flow(user, flow, (first, second))
    blocks.limit(flow, ConsecutiveLossLimit(int(losses), int(hours), int(minutes)))


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "(?P<flow>[^"]+)" attivo con asset "(?P<first>[^"]+)" e '
        r'"(?P<second>[^"]+)"$'
    )
)
def active_flow(blocks: ReopeningBlocks, user: str, flow: str, first: str, second: str) -> None:
    blocks.add_flow(user, flow, (first, second))


@given(parsers.re(rf'^che "(?P<flow>[^"]+)" ha {LIMIT}$'))
def flow_with_limit(blocks: ReopeningBlocks, flow: str, losses: str, hours: str, minutes: str) -> None:
    blocks.limit(flow, ConsecutiveLossLimit(int(losses), int(hours), int(minutes)))


@given(quoted('che "{flow}" ha chiuso in perdita due posizioni short su "{asset}", alle 13:00 e alle 13:30 di oggi'))
def two_short_losses(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    for clock in ("13:00", "13:30"):
        blocks.closed(flow, "short", asset, at(clock))


@given(
    quoted(
        'che "{flow}" ha invece chiuso in perdita una posizione short su "{first}" alle 13:00 e una posizione short su '
        '"{second}" alle 13:30'
    )
)
def losses_on_two_assets(blocks: ReopeningBlocks, flow: str, first: str, second: str) -> None:
    blocks.closed_instead(flow)
    blocks.closed(flow, "short", first, at("13:00"))
    blocks.closed(flow, "short", second, at("13:30"))


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha invece chiuso tre posizioni short su "(?P<asset>[^"]+)": in perdita alle 12:00, '
        r"(?P<result>in utile|in pari) alle 13:00 e in perdita alle 13:30$"
    )
)
def interrupted_losses(blocks: ReopeningBlocks, flow: str, asset: str, result: str) -> None:
    blocks.closed_instead(flow)
    blocks.closed(flow, "short", asset, at("12:00"))
    blocks.closed(flow, "short", asset, at("13:00"), RESULT_OF[result])
    blocks.closed(flow, "short", asset, at("13:30"))


@given(quoted('che "{flow}" ha invece chiuso in perdita due posizioni short su "{asset}", 30 ore fa e 1 ora fa'))
def loss_out_of_window(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    blocks.closed_instead(flow)
    now = at(BLOCKED_HOUR)
    blocks.closed(flow, "short", asset, now - timedelta(hours=30))
    blocks.closed(flow, "short", asset, now - timedelta(hours=1))


@given(quoted('che "{flow}" ha ambito del conteggio "{scope}"'))
def counting_scope(blocks: ReopeningBlocks, flow: str, scope: str) -> None:
    blocks.limit(flow, replace(blocks.limit_of(flow), count_scope=LossCountScope.named(scope)))


@given(quoted('che "{flow}" ha aperto short su "{asset}" alle 15:31 e la posizione si è chiusa in perdita alle 16:00'))
def third_loss(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    blocks.closed(flow, "short", asset, at("16:00"))


@given(quoted('che "{flow}" ha una posizione long su "{asset}"'))
def long_position(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    blocks.stops.open_long(flow, asset, PRICE)


@given(quoted('che "{flow}" non ha il blocco delle riaperture'))
def without_limit(blocks: ReopeningBlocks, flow: str) -> None:
    blocks.limit(flow, None)


@given(quoted('che il flusso "{flow}" esisteva prima del blocco delle riaperture'))
def flow_from_before(blocks: ReopeningBlocks, flow: str) -> None:
    # A version saved before reads the limit as absent (ADR limite-di-perdite-consecutive-del-flusso).
    blocks.limit(flow, None)
    blocks.version_before = blocks.flow_cycles.flow(flow).configuration.version


@given(quoted('che "{flow}" ha le riaperture short su "{asset}" ferme fino alle 15:30'))
def reopenings_stopped(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    blocks.ensure_flow("anna", flow)
    blocks.limit(flow, ConsecutiveLossLimit(2, 24, 120))
    two_short_losses(blocks, flow, asset)


# When


@when(
    parsers.re(
        r'^alle (?P<clock>\d+:\d+) l\'agente di "(?P<flow>[^"]+)" decide di aprire (?P<side>long|short) su '
        r'"(?P<asset>[^"]+)"$'
    )
)
def agent_opens_at(blocks: ReopeningBlocks, clock: str, flow: str, side: str, asset: str) -> None:
    blocks.decides(flow, "apri", side, asset, clock)


@when(quoted('l\'agente di "{flow}" decide di aprire short su "{asset}"'))
def agent_opens(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    blocks.decides(flow, "apri", "short", asset, BLOCKED_HOUR)


@when(quoted('alle 14:00 l\'agente di "{flow}" decide di invertire la posizione su "{asset}"'))
def agent_reverses(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    blocks.decides(flow, "inverti", None, asset, BLOCKED_HOUR)


@when(quoted('alle 14:00 parte il ciclo di "{flow}"'))
def cycle_starts(blocks: ReopeningBlocks, flow: str) -> None:
    blocks.flow_cycles.run(flow, BLOCKED_HOUR)


@when(
    quoted('"{user}" crea il flusso "{flow}" senza indicare perdite consecutive massime, finestra e durata del blocco')
)
def creates_without_limit(blocks: ReopeningBlocks, user: str, flow: str) -> None:
    flow_cycles = blocks.flow_cycles
    command = CreateFlowCommand(
        name=flow,
        account_id=flow_cycles.account_of(user),
        assets=("ETH",),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
    )
    blocks.read = flow_cycles.platform.use_cases_of(user).create_flow.execute(command)


@when(quoted('"{user}" legge la configurazione di "{flow}"'))
def reads_configuration(blocks: ReopeningBlocks, user: str, flow: str) -> None:
    command = GetFlowCommand(blocks.flow_cycles.flow(flow).id)
    blocks.read = blocks.flow_cycles.platform.use_cases_of(user).get_flow.execute(command)


@when(
    quoted(
        '"{user}" imposta le perdite consecutive massime di "{flow}" a {losses} senza finestra e senza durata del '
        "blocco"
    )
)
def sets_losses_alone(blocks: ReopeningBlocks, user: str, flow: str, losses: str) -> None:
    blocks.modify(user, flow, ConsecutiveLossLimitRequest(max_consecutive_losses=int(losses)))


@when(parsers.re(rf'^"(?P<user>[^"]+)" imposta per "(?P<flow>[^"]+)" {LIMIT}$'))
@when(parsers.re(rf'^"(?P<user>[^"]+)" imposta per "(?P<flow>[^"]+)" {LIMIT} senza ambito$'))
def sets_limit(  # noqa: PLR0917 - one argument per value of the step
    blocks: ReopeningBlocks, user: str, flow: str, losses: str, hours: str, minutes: str
) -> None:
    blocks.modify(user, flow, ConsecutiveLossLimitRequest(int(losses), int(hours), int(minutes)))


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" imposta per "(?P<flow>[^"]+)" perdite consecutive massime (?P<losses>\d+), finestra '
        r'(?P<hours>\d+) ore, durata del blocco (?P<minutes>\d+) minuti e ambito del conteggio "(?P<scope>[^"]+)"$'
    )
)
def sets_limit_with_scope(  # noqa: PLR0917 - one argument per value of the step
    blocks: ReopeningBlocks, user: str, flow: str, losses: str, hours: str, minutes: str, scope: str
) -> None:
    blocks.modify(user, flow, ConsecutiveLossLimitRequest(int(losses), int(hours), int(minutes), scope))


@when(
    quoted(
        '"{user}" imposta l\'ambito del conteggio di "{flow}" a "{scope}" senza perdite consecutive massime, '
        "finestra e durata del blocco"
    )
)
def sets_scope_alone(blocks: ReopeningBlocks, user: str, flow: str, scope: str) -> None:
    blocks.modify(user, flow, ConsecutiveLossLimitRequest(count_scope=scope))


@when(quoted('"{user}" toglie il blocco delle riaperture di "{flow}"'))
def removes_limit(blocks: ReopeningBlocks, user: str, flow: str) -> None:
    blocks.modify(user, flow, ConsecutiveLossLimitRequest(remove_limit=True))


@when(parsers.re(rf'^il client MCP di "(?P<user>[^"]+)" imposta per "(?P<flow>[^"]+)" {LIMIT}$'))
def mcp_sets_limit(  # noqa: PLR0917 - one argument per value of the step
    blocks: ReopeningBlocks, user: str, flow: str, losses: str, hours: str, minutes: str
) -> None:
    blocks.ensure_flow(user, flow)
    flow_id = str(blocks.flow_cycles.flow(flow).id.value)
    limit = {"max_consecutive_losses": int(losses), "loss_window_hours": int(hours), "block_minutes": int(minutes)}
    arguments = {"flow_id": flow_id, "modification": {"consecutive_loss_limit": limit}}
    result = blocks.mcp().call_as(user, "modify_flow", arguments)
    assert not result.is_error, body_of(result)
    blocks.read_flow = body_of(blocks.mcp().call_as(user, "get_flow", {"flow_id": flow_id}))


@when(quoted('alle 14:00 il client MCP di "{user}" legge lo stato di "{flow}"'))
def mcp_reads_state(blocks: ReopeningBlocks, user: str, flow: str) -> None:
    blocks.flow_cycles.platform.now = at(BLOCKED_HOUR)
    flow_id = str(blocks.flow_cycles.flow(flow).id.value)
    result = blocks.mcp().call_as(user, "read_flow_state", {"flow_id": flow_id})
    assert not result.is_error, body_of(result)
    blocks.read_blocks = [block["text"] for block in body_of(result)["reopening_blocks"]]


# Then


@then(quoted('la decisione su "{asset}" viene bloccata con "{reason}"'))
def decision_blocked(blocks: ReopeningBlocks, asset: str, reason: str) -> None:
    outcome = blocks.outcome("alfa", CycleStep.RISK_CHECK, "esiti", asset)
    assert (outcome["tipo"], outcome["reason"]) == ("BlockedDecision", reason)


@then(quoted('la decisione su "{asset}" viene approvata'))
def decision_approved(blocks: ReopeningBlocks, asset: str) -> None:
    assert blocks.outcome("alfa", CycleStep.RISK_CHECK, "esiti", asset)["tipo"] == "ApprovedOpening"


@then(quoted('sull\'exchange non c\'è nessuna posizione di "{flow}" su "{asset}"'))
def no_position(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    assert blocks.held(flow, asset) is None


@then(quoted('la posizione long di "{flow}" su "{asset}" viene chiusa'))
def long_closed(blocks: ReopeningBlocks, flow: str, asset: str) -> None:
    assert blocks.outcome(flow, CycleStep.RISK_CHECK, "esiti", asset)["tipo"] == "ApprovedClose"
    [closing] = [order for order in blocks.flow_cycles.platform.order_exchange.sent if order.coin == asset][-1:]
    assert closing.reduce_only


@then(quoted('il ciclo di "{flow}" registra "{reason}"'))
def reversal_blocked(blocks: ReopeningBlocks, flow: str, reason: str) -> None:
    outcome = blocks.outcome(flow, CycleStep.ORDER_EXECUTION, "inversioni", "NEAR")
    assert (outcome["tipo"], outcome["reason"]) == ("BlockedDecision", reason)


@then(quoted('lo stato del flusso inviato all\'agente riporta "{text}"'))
def block_in_context(blocks: ReopeningBlocks, text: str) -> None:
    assert blocks.stopped_in_context() == [text]


@then("lo stato del flusso inviato all'agente non riporta riaperture ferme")
def no_block_in_context(blocks: ReopeningBlocks) -> None:
    assert blocks.stopped_in_context() is None


@then(quoted('il flusso "{flow}" non ha il blocco delle riaperture'))
@then(quoted('"{flow}" non ha il blocco delle riaperture'))
def no_limit(blocks: ReopeningBlocks, flow: str) -> None:
    assert blocks.read is not None
    assert blocks.read.name.value == flow
    assert blocks.read.configuration.consecutive_loss_limit is None


@then(quoted('la configurazione di "{flow}" resta alla stessa versione'))
def same_version(blocks: ReopeningBlocks, flow: str) -> None:
    assert blocks.flow_cycles.flow(flow).configuration.version == blocks.version_before


@then(quoted('la modifica viene rifiutata con "{message}"'))
def refused(blocks: ReopeningBlocks, message: str) -> None:
    assert blocks.error is not None
    assert str(blocks.error) == message
    assert blocks.flow_cycles.flow("alfa").configuration.version == blocks.version_before


@then(parsers.re(rf'^"(?P<flow>[^"]+)" ha una nuova versione della configurazione con {LIMIT}$'))
def new_version_with_limit(blocks: ReopeningBlocks, flow: str, losses: str, hours: str, minutes: str) -> None:
    configuration = blocks.flow_cycles.flow(flow).configuration
    assert configuration.version == blocks.version_before + 1
    assert configuration.consecutive_loss_limit == ConsecutiveLossLimit(int(losses), int(hours), int(minutes))


@then(quoted('"{flow}" ha il blocco delle riaperture con ambito del conteggio "{scope}"'))
def limit_with_scope(blocks: ReopeningBlocks, flow: str, scope: str) -> None:
    assert blocks.limit_of(flow).count_scope.value == scope


@then(quoted('"{flow}" ha una nuova versione della configurazione senza il blocco delle riaperture'))
def new_version_without_limit(blocks: ReopeningBlocks, flow: str) -> None:
    configuration = blocks.flow_cycles.flow(flow).configuration
    assert configuration.version == blocks.version_before + 1
    assert configuration.consecutive_loss_limit is None


@then(parsers.re(rf'^il dettaglio di "(?P<flow>[^"]+)" letto dagli strumenti riporta {LIMIT}$'))
def tools_detail(blocks: ReopeningBlocks, flow: str, losses: str, hours: str, minutes: str) -> None:
    assert blocks.read_flow["name"] == flow
    assert blocks.read_flow["consecutive_loss_limit"] == {
        "max_consecutive_losses": int(losses),
        "loss_window_hours": int(hours),
        "block_minutes": int(minutes),
        "count_scope": "asset",
    }


@then(quoted('lo stato riporta "{text}"'))
def state_reports(blocks: ReopeningBlocks, text: str) -> None:
    assert blocks.read_blocks == [text]
