"""ADR-massimo-profitto-raggiunto-nello-stato-della-posizione: the domain computes the largest profit a position reached
and the surveillance records it with the best price; the one reading of the state adds it only when the flow has
distance or breakeven, and API and MCP show it as that reading gives it; the agent receives it only with the option.
"""

import inspect
import re

from autotrading.adapters.inbound.api import flow_state
from autotrading.adapters.inbound.mcp import reading_views
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.domain.agent import agent_context
from autotrading.domain.flows import cycle_flow
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.flows.watched_position import WatchedPosition

AGENT_KEY = '"massimo_profitto_raggiunto"'
# A difference with the entry price, or the best price itself: the profit computed from prices.
PROFIT_FROM_PRICES = re.compile(r"entry_price\s*-|-\s*[\w.]*entry_price|best_price")


def _computes_the_profit(source: str) -> bool:
    """Whether a module computes the profit from prices, instead of reading the one the domain computed."""
    return PROFIT_FROM_PRICES.search(source) is not None


def test_adr_massimo_profitto_raggiunto_the_domain_computes_it_with_the_best_price() -> None:
    seen = inspect.getsource(WatchedPosition.seen)

    assert "best_price" in seen
    assert "max(gained, ZERO)" in seen


def test_adr_massimo_profitto_raggiunto_the_state_adds_it_only_with_distance_or_breakeven() -> None:
    watched_of = inspect.getsource(ReadFlowStateUseCase)

    assert "if not flow.configuration.trailing_stop.active:" in watched_of
    assert "return {}" in watched_of


def test_adr_massimo_profitto_raggiunto_api_and_mcp_show_it_as_the_state_gives_it() -> None:
    for module in (flow_state, reading_views):
        source = inspect.getsource(module)
        assert "state.max_profit_of(position.asset)" in source
        assert not _computes_the_profit(source)


def test_adr_massimo_profitto_raggiunto_an_adapter_that_computes_it_is_found() -> None:
    computed = "max_profit_reached=str((position.mark_price - position.entry_price) * position.size)"

    assert _computes_the_profit(computed)


def test_adr_massimo_profitto_raggiunto_the_agent_receives_it_only_with_the_option() -> None:
    option = inspect.getsource(TrailingStop).split("def max_profit_for_agent", 1)[1].split("def ", 1)[0]

    assert "self.active and self.max_profit_in_context" in option
    assert "max_profit_for_agent" in inspect.getsource(cycle_flow)
    context = inspect.getsource(agent_context)

    assert f"{{}} if position.max_profit is None else {{{AGENT_KEY}" in context
