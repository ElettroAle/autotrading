"""ADR-controllo-delle-riaperture-dopo-perdite-consecutive: the domain says which blocks are in force from the closed
positions of the flow and the instant; the risk check receives them and blocks an opening on a blocked side before any
limit; the one reading of the state reads the closings only for a flow with the limit, and API, MCP and the agent show
the blocks with the text of the domain.
"""

import inspect
import re

from autotrading.adapters.inbound.api import reopening_block_response
from autotrading.adapters.inbound.mcp import reading_views
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.domain.agent import agent_context
from autotrading.domain.flows import cycle_flow
from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.risk_check import RiskCheck, RiskState

# A text of a block composed by an adapter: the words of the domain repeated outside it.
TEXT_OUTSIDE_THE_DOMAIN = re.compile(r"ferme fino alle|perdit[ae] consecutiv|bloccata:")


def _composes_the_text(source: str) -> bool:
    return TEXT_OUTSIDE_THE_DOMAIN.search(source) is not None


def test_adr_controllo_delle_riaperture_the_domain_counts_the_net_losses_from_the_most_recent_closing() -> None:
    in_force = inspect.getsource(ReopeningBlock)

    assert "takewhile" in in_force
    assert "net_pnl < 0" in in_force
    assert "reverse=True" in in_force
    assert "block_duration" in in_force


def test_adr_controllo_delle_riaperture_the_risk_check_blocks_the_side_before_the_limits() -> None:
    opening = inspect.getsource(RiskCheck._opening)

    assert "reopening_blocks" in inspect.getsource(RiskState)
    assert opening.index("reopening_block_of") < opening.index("_open(")
    assert "BlockedDecision(intent.asset, block.opening_reason(intent.asset))" in opening


def test_adr_controllo_delle_riaperture_only_a_flow_with_the_limit_reads_its_closings() -> None:
    reading = inspect.getsource(ReadFlowStateUseCase._reopening_blocks_of)

    assert reading.index("if limit is None:") < reading.index("closed_within(")
    assert "ReopeningBlock.in_force(" in reading


def test_adr_controllo_delle_riaperture_api_mcp_and_agent_show_the_text_of_the_domain() -> None:
    for module in (reopening_block_response, reading_views):
        source = inspect.getsource(module)
        assert "block.state_text" in source
        assert not _composes_the_text(source)
    assert "state_text" in inspect.getsource(cycle_flow)
    assert '"riaperture_ferme"' in inspect.getsource(agent_context)


def test_adr_controllo_delle_riaperture_a_text_composed_by_an_adapter_is_found() -> None:
    assert _composes_the_text('text=f"riaperture {block.side} ferme fino alle {block.until:%H:%M}"')
