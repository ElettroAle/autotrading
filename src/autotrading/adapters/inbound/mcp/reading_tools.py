"""The tools that read the data of the user: one for each reading of the API, on the same use case and command."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, ToolAnnotations

from autotrading.adapters.inbound.mcp.flow_views import FlowView
from autotrading.adapters.inbound.mcp.reading_filters import ClosedPositionFilters, CycleFilters
from autotrading.adapters.inbound.mcp.reading_views import (
    AccountListView,
    AccountView,
    ClosedPositionPageView,
    CycleDetailView,
    CyclePageView,
    FlowListView,
    FlowOverviewView,
    FlowRankingView,
    FlowStateView,
    FlowStatisticsView,
    RankingView,
)
from autotrading.adapters.inbound.mcp.tool_results import answer_of
from autotrading.adapters.inbound.mcp.use_cases import McpUseCases
from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.application.flows.list_cycles import ListCyclesCommand
from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsCommand
from autotrading.application.flows.rank_flows import RankFlowsCommand
from autotrading.application.flows.read_cycle import ReadCycleCommand
from autotrading.application.flows.read_flow_memory import FlowMemoryReading, ReadFlowMemoryCommand
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.application.flows.read_flow_statistics import ReadFlowStatisticsCommand
from autotrading.domain.flows.flow_id import FlowId

READING = ToolAnnotations(read_only_hint=True, open_world_hint=False)
PERIOD = (
    "Periodo: 30m, 1h, 6h, 12h, 24h, 7d, 30d, all (predefinito) o range; con range since e until, istanti ISO 8601."
)


def install_reading_tools(server: MCPServer, use_cases: Callable[[], McpUseCases]) -> None:
    @server.tool(
        description=f"Elenco dei flussi in uso con stato, valore, PnL dall'avvio e ultimi cicli. {PERIOD}",
        annotations=READING,
    )
    def list_flows(
        period: str = "all", since: datetime | None = None, until: datetime | None = None
    ) -> Annotated[CallToolResult, FlowListView]:
        def read() -> FlowListView:
            overviews = use_cases().list_flow_overviews.execute(ListFlowOverviewsCommand(period, since, until))
            return FlowListView([FlowOverviewView.of(each) for each in overviews])

        return answer_of(read)

    @server.tool(
        description="Dettaglio di un flusso con la versione della configurazione in vigore.", annotations=READING
    )
    def get_flow(flow_id: UUID) -> Annotated[CallToolResult, FlowView]:
        return answer_of(lambda: FlowView.of(use_cases().get_flow.execute(GetFlowCommand(FlowId(flow_id)))))

    @server.tool(
        description=f"Stato di un flusso letto ora: capitale, liquidità, posizioni aperte e risultati. {PERIOD}",
        annotations=READING,
    )
    def read_flow_state(
        flow_id: UUID, period: str = "all", since: datetime | None = None, until: datetime | None = None
    ) -> Annotated[CallToolResult, FlowStateView]:
        def read() -> FlowStateView:
            command = ReadFlowResultsCommand(flow_id, period, since, until)
            return FlowStateView.of(use_cases().read_flow_results.execute(command))

        return answer_of(read)

    @server.tool(
        description="Posizioni chiuse di un flusso, dalla chiusura più recente, a pagine, con filtri facoltativi.",
        annotations=READING,
    )
    def list_closed_positions(
        flow_id: UUID, page: int = 1, filters: ClosedPositionFilters | None = None
    ) -> Annotated[CallToolResult, ClosedPositionPageView]:
        def read() -> ClosedPositionPageView:
            criteria = (filters or ClosedPositionFilters()).criteria()
            command = ListClosedPositionsCommand(flow_id, page, criteria)
            return ClosedPositionPageView.of(use_cases().list_closed_positions.execute(command))

        return answer_of(read)

    @server.tool(
        description="Cicli di un flusso con esito e decisioni, dal più recente, a pagine, con filtri facoltativi.",
        annotations=READING,
    )
    def list_cycles(
        flow_id: UUID, page: int = 1, filters: CycleFilters | None = None
    ) -> Annotated[CallToolResult, CyclePageView]:
        def read() -> CyclePageView:
            command = ListCyclesCommand(flow_id, page, (filters or CycleFilters()).criteria())
            return CyclePageView.of(use_cases().list_cycles.execute(command))

        return answer_of(read)

    @server.tool(
        description="Un ciclo di un flusso con tutto ciò che ha registrato, decisioni dell'agente comprese.",
        annotations=READING,
    )
    def read_cycle(flow_id: UUID, planned_at: datetime) -> Annotated[CallToolResult, CycleDetailView]:
        return answer_of(
            lambda: CycleDetailView.of(use_cases().read_cycle.execute(ReadCycleCommand(flow_id, planned_at)))
        )

    @server.tool(
        description="Memoria del flusso: le decisioni operative precedenti per asset, con il loro esito, che l'agente "
        "riceverebbe se il ciclo partisse ora; vuota se la memoria non è attiva.",
        annotations=READING,
    )
    def read_flow_memory(flow_id: UUID) -> Annotated[CallToolResult, FlowMemoryReading]:
        return answer_of(lambda: use_cases().read_flow_memory.execute(ReadFlowMemoryCommand(FlowId(flow_id))))

    @server.tool(description=f"Statistiche di un flusso nel periodo. {PERIOD}", annotations=READING)
    def read_flow_statistics(
        flow_id: UUID, period: str = "all", since: datetime | None = None, until: datetime | None = None
    ) -> Annotated[CallToolResult, FlowStatisticsView]:
        def read() -> FlowStatisticsView:
            command = ReadFlowStatisticsCommand(flow_id, period, since, until)
            return FlowStatisticsView.of(use_cases().read_flow_statistics.execute(command))

        return answer_of(read)

    @server.tool(description=f"Classifica dei flussi nel periodo. {PERIOD}", annotations=READING)
    def rank_flows(
        period: str = "all", since: datetime | None = None, until: datetime | None = None
    ) -> Annotated[CallToolResult, RankingView]:
        def read() -> RankingView:
            rankings = use_cases().rank_flows.execute(RankFlowsCommand(period, since, until))
            return RankingView([FlowRankingView.of(each) for each in rankings])

        return answer_of(read)

    @server.tool(description="Conti dell'utente con il capitale assegnato ai loro flussi.", annotations=READING)
    def list_accounts() -> Annotated[CallToolResult, AccountListView]:
        return answer_of(
            lambda: AccountListView([AccountView.of(each) for each in use_cases().list_accounts.execute()])
        )
