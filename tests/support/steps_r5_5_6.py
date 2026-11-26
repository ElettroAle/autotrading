"""R5.5.6: a flow may give its agent the round-trip cost of a position, from the fee the exchange applies to its account
for a market order; run as the worker, the API and the MCP server compose them (ADR
costo-di-andata-e-ritorno-nel-contesto-dell-agente).
"""

import json
from dataclasses import dataclass, replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.create_flow import CreateFlowCommand
from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.flow import Flow
from tests.support.flow_cycles import FlowCycles
from tests.support.flows import OPENROUTER_MODEL
from tests.support.mcp_session import McpSession, body_of
from tests.support.platform import HYPERLIQUID
from tests.support.steps import quoted
from tests.support.steps_r3_1_2 import NO_DECISIONS

USER = "anna"
CYCLE_HOUR = "14:00"
NEW_ASSET = "AVAX"
STATE_OF = {"accese": True, "spente": False}
COST = "costo_di_andata_e_ritorno_percento"
MISSING = "dati_mancanti"


@dataclass
class RoundTripCostSteps:
    """The flow of the user, the cycles that run it, and what the user changed and read."""

    flow_cycles: FlowCycles
    version_before: int = 0
    created: Flow | None = None
    read: Flow | None = None
    read_flow: dict[str, object] | None = None

    def ensure_flow(self, flow: str, asset: str = "BTC") -> Flow:
        """The flow active on its asset, added once."""
        if flow not in self.flow_cycles.users:
            self.flow_cycles.add_flow(USER, flow, assets=(asset,))
            markets = self.flow_cycles.platform.markets[HYPERLIQUID]
            markets.assets = markets.assets | {asset}
            self.flow_cycles.model.text = NO_DECISIONS
        return self.flow_cycles.flow(flow)

    def address(self, flow: str) -> str:
        return self.flow_cycles.credentials_of(flow).value("account_address")

    def option(self, flow: str, shown: bool) -> None:
        """The option as the flow holds it now, without a new version."""
        self.flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, fees_for_agent=shown))

    def turn_on(self, user: str, flow: str) -> None:
        recorded = self.ensure_flow(flow)
        self.version_before = recorded.configuration.version
        command = ModifyFlowCommand(recorded.id, fees_for_agent=True)
        self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)

    def state_in_context(self) -> dict[str, object]:
        state = self.flow_cycles.context()["stato_del_flusso"]
        assert isinstance(state, dict)
        return state

    def missing_in_context(self) -> list[str]:
        missing = self.flow_cycles.context()[MISSING]
        assert isinstance(missing, list)
        return missing

    def mcp(self) -> McpSession:
        return McpSession(self.flow_cycles.platform)


def percent_of(text: str) -> Decimal:
    """A percent as the scenarios write it, with the decimal comma."""
    return Decimal(text.replace(",", "."))


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def fees(flow_cycles: FlowCycles) -> RoundTripCostSteps:
    return RoundTripCostSteps(flow_cycles)


# Given


@given(quoted('che "{user}" ha il flusso "{flow}" attivo con asset "{asset}"'))
def active_flow(fees: RoundTripCostSteps, user: str, flow: str, asset: str) -> None:
    assert user == USER
    fees.ensure_flow(flow, asset)


@given(
    parsers.re(
        r'^che l\'exchange applica al conto di "(?P<flow>[^"]+)" una commissione dello (?P<percent>[\d,]+)% per un '
        r"ordine a mercato$"
    )
)
def market_order_fee(fees: RoundTripCostSteps, flow: str, percent: str) -> None:
    rates = fees.flow_cycles.platform.activity_reader.market_order_fee_rates
    rates[fees.address(flow)] = percent_of(percent) / 100


@given(parsers.re(r'^che "(?P<flow>[^"]+)" ha le commissioni nel contesto dell\'agente (?P<state>accese|spente)$'))
def agent_option(fees: RoundTripCostSteps, flow: str, state: str) -> None:
    fees.option(flow, STATE_OF[state])


@given(quoted("che l'exchange non risponde alla lettura delle commissioni del conto"))
def fees_unreachable(fees: RoundTripCostSteps) -> None:
    fees.flow_cycles.platform.activity_reader.market_order_fee_reachable = False


@given(quoted('che il flusso "{flow}" esisteva prima dell\'opzione delle commissioni'))
def flow_from_before(fees: RoundTripCostSteps, flow: str) -> None:
    # A version saved before reads the option as off (ADR costo-di-andata-e-ritorno-nel-contesto-dell-agente).
    fees.ensure_flow(flow)
    fees.option(flow, shown=False)
    fees.version_before = fees.flow_cycles.flow(flow).configuration.version


# When


@when(quoted('parte il ciclo di "{flow}"'))
def cycle_starts(fees: RoundTripCostSteps, flow: str) -> None:
    fees.flow_cycles.run(flow, CYCLE_HOUR)


@when(quoted('"{user}" crea il flusso "{flow}" senza indicare le commissioni nel contesto dell\'agente'))
def creates_flow(fees: RoundTripCostSteps, user: str, flow: str) -> None:
    flow_cycles = fees.flow_cycles
    account_id = fees.ensure_flow("alfa").assigned_account_id
    markets = flow_cycles.platform.markets[HYPERLIQUID]
    markets.assets = markets.assets | {NEW_ASSET}
    command = CreateFlowCommand(
        name=flow,
        account_id=account_id,
        assets=(NEW_ASSET,),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
    )
    fees.created = flow_cycles.platform.use_cases_of(user).create_flow.execute(command)


@when(quoted('"{user}" legge la configurazione di "{flow}"'))
def reads_configuration(fees: RoundTripCostSteps, user: str, flow: str) -> None:
    command = GetFlowCommand(fees.flow_cycles.flow(flow).id)
    fees.read = fees.flow_cycles.platform.use_cases_of(user).get_flow.execute(command)


@when(quoted('"{user}" accende per "{flow}" le commissioni nel contesto dell\'agente'))
def turns_on(fees: RoundTripCostSteps, user: str, flow: str) -> None:
    fees.turn_on(user, flow)


@when(quoted('il client MCP di "{user}" accende per "{flow}" le commissioni nel contesto dell\'agente'))
def mcp_turns_on(fees: RoundTripCostSteps, user: str, flow: str) -> None:
    flow_id = str(fees.ensure_flow(flow).id.value)
    arguments = {"flow_id": flow_id, "modification": {"fees_for_agent": True}}
    result = fees.mcp().call_as(user, "modify_flow", arguments)
    assert not result.is_error, body_of(result)
    fees.read_flow = body_of(fees.mcp().call_as(user, "get_flow", {"flow_id": flow_id}))


# Then


@then(parsers.re(r"^lo stato del flusso inviato all'agente riporta il costo di andata e ritorno (?P<percent>[\d,]+)%$"))
def cost_in_context(fees: RoundTripCostSteps, percent: str) -> None:
    assert Decimal(str(fees.state_in_context()[COST])) == percent_of(percent)


@then(
    parsers.re(
        r"^lo stato del flusso inviato all'agente non riporta il costo di andata e ritorno (?P<percent>[\d,]+)%$"
    )
)
def no_cost_in_context(fees: RoundTripCostSteps, percent: str) -> None:
    state = fees.state_in_context()
    assert COST not in state
    assert str(percent_of(percent)) not in json.dumps(state)
    assert "andata e ritorno" not in fees.flow_cycles.system_text() + json.dumps(fees.flow_cycles.context())


@then(quoted('i dati mancanti del ciclo riportano "{datum}"'))
def datum_missing(fees: RoundTripCostSteps, datum: str) -> None:
    assert [entry for entry in fees.missing_in_context() if entry.startswith(f"{datum}: ")]
    assert COST not in fees.state_in_context()


@then(quoted('il ciclo di "{flow}" si conclude'))
def cycle_completed(fees: RoundTripCostSteps, flow: str) -> None:
    assert fees.flow_cycles.last_record(flow).outcome is CycleOutcome.COMPLETED


@then(quoted('il flusso "{flow}" ha le commissioni nel contesto dell\'agente spente'))
def created_off(fees: RoundTripCostSteps, flow: str) -> None:
    assert fees.created is not None
    assert fees.created.name.value == flow
    assert fees.created.configuration.fees_for_agent is False


@then(quoted('"{flow}" ha le commissioni nel contesto dell\'agente spente'))
def read_off(fees: RoundTripCostSteps, flow: str) -> None:
    assert fees.read is not None
    assert fees.read.name.value == flow
    assert fees.read.configuration.fees_for_agent is False


@then(quoted('la configurazione di "{flow}" resta alla stessa versione'))
def same_version(fees: RoundTripCostSteps, flow: str) -> None:
    assert fees.flow_cycles.flow(flow).configuration.version == fees.version_before


@then(quoted('"{flow}" ha una nuova versione della configurazione con le commissioni nel contesto dell\'agente accese'))
def new_version_with_option(fees: RoundTripCostSteps, flow: str) -> None:
    configuration = fees.flow_cycles.flow(flow).configuration
    assert configuration.version == fees.version_before + 1
    assert configuration.fees_for_agent is True


@then(quoted('il dettaglio di "{flow}" letto dagli strumenti riporta le commissioni nel contesto dell\'agente accese'))
def tools_detail(fees: RoundTripCostSteps, flow: str) -> None:
    assert fees.read_flow is not None
    assert fees.read_flow["name"] == flow
    assert fees.read_flow["fees_for_agent"] is True
