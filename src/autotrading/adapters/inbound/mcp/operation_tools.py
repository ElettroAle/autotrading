"""The tools that operate on the flows: one for each operation of the API, on the same use case and command."""

from collections.abc import Callable
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, ToolAnnotations

from autotrading.adapters.inbound.mcp.access import request_identity
from autotrading.adapters.inbound.mcp.flow_requests import FlowCreation, FlowModification, StrategyImport
from autotrading.adapters.inbound.mcp.flow_views import CashOutView, FlowView, OpeningsResumedView, StopOutcomeView
from autotrading.adapters.inbound.mcp.reading_views import CycleSummaryView
from autotrading.adapters.inbound.mcp.tool_results import answer_of
from autotrading.adapters.inbound.mcp.use_cases import McpUseCases
from autotrading.application.flows.archive_flow import ArchiveFlowCommand
from autotrading.application.flows.cash_out_profits import CashOutProfitsCommand
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.application.flows.duplicate_flow import DuplicateFlowCommand
from autotrading.application.flows.request_on_demand_cycle import RequestOnDemandCycleCommand
from autotrading.application.flows.resume_flow_openings import ResumeFlowOpeningsCommand
from autotrading.application.flows.stop_flow import StopFlowCommand
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_id import FlowId

CHANGING = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
TRADING = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)
ENDING = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False)


def install_operation_tools(server: MCPServer, use_cases: Callable[[], McpUseCases]) -> None:
    _install_configuration_tools(server, use_cases)
    _install_status_tools(server, use_cases)
    _install_capital_tools(server, use_cases)


def _install_configuration_tools(server: MCPServer, use_cases: Callable[[], McpUseCases]) -> None:
    @server.tool(description="Crea un flusso fermo su un conto dell'utente.", annotations=CHANGING)
    def create_flow(flow: FlowCreation) -> Annotated[CallToolResult, FlowView]:
        return answer_of(lambda: FlowView.of(use_cases().create_flow.execute(flow.command())))

    @server.tool(
        description="Crea una bozza con il nome dato e la strategia di un file di strategia (sezione strategy).",
        annotations=CHANGING,
    )
    def import_flow_strategy(name: str, strategy: StrategyImport) -> Annotated[CallToolResult, FlowView]:
        return answer_of(lambda: FlowView.of(use_cases().import_flow_strategy.execute(strategy.command(name))))

    @server.tool(description="Duplica un flusso in una bozza con la stessa configurazione.", annotations=CHANGING)
    def duplicate_flow(flow_id: UUID) -> Annotated[CallToolResult, FlowView]:
        return answer_of(lambda: FlowView.of(use_cases().duplicate_flow.execute(DuplicateFlowCommand(FlowId(flow_id)))))

    @server.tool(
        description=(
            "Modifica le parti date di un flusso; le altre restano quelle della versione in vigore. Le parti in remove "
            "tornano a nessun valore, o al predefinito per il system prompt."
        ),
        annotations=CHANGING,
    )
    def modify_flow(flow_id: UUID, modification: FlowModification) -> Annotated[CallToolResult, FlowView]:
        return answer_of(lambda: FlowView.of(use_cases().modify_flow.execute(modification.command(flow_id))))


def _install_status_tools(server: MCPServer, use_cases: Callable[[], McpUseCases]) -> None:
    def changed_status(flow_id: UUID, action: FlowAction) -> CallToolResult:
        command = ChangeFlowStatusCommand(FlowId(flow_id), action)
        return answer_of(lambda: FlowView.of(use_cases().change_flow_status.execute(command)))

    @server.tool(description="Avvia un flusso fermo.", annotations=TRADING)
    def start_flow(flow_id: UUID) -> Annotated[CallToolResult, FlowView]:
        return changed_status(flow_id, FlowAction.START)

    @server.tool(description="Mette in pausa un flusso attivo.", annotations=CHANGING)
    def pause_flow(flow_id: UUID) -> Annotated[CallToolResult, FlowView]:
        return changed_status(flow_id, FlowAction.PAUSE)

    @server.tool(description="Riprende un flusso in pausa.", annotations=TRADING)
    def resume_flow(flow_id: UUID) -> Annotated[CallToolResult, FlowView]:
        return changed_status(flow_id, FlowAction.RESUME)

    @server.tool(description="Ferma un flusso dopo il ciclo in corso e ne chiude le posizioni.", annotations=TRADING)
    def stop_flow(flow_id: UUID) -> Annotated[CallToolResult, StopOutcomeView]:
        def stop() -> StopOutcomeView:
            command = StopFlowCommand(FlowId(flow_id), request_identity().user_id)
            return StopOutcomeView.of(use_cases().stop_flow.execute(command))

        return answer_of(stop)

    @server.tool(description="Archivia un flusso fermo, in modo definitivo.", annotations=ENDING)
    def archive_flow(flow_id: UUID) -> Annotated[CallToolResult, FlowView]:
        return answer_of(lambda: FlowView.of(use_cases().archive_flow.execute(ArchiveFlowCommand(FlowId(flow_id)))))

    @server.tool(
        description="Esegue ora un ciclo del flusso attivo e ne restituisce l'esito quando finisce.",
        annotations=TRADING,
    )
    def run_cycle_now(flow_id: UUID) -> Annotated[CallToolResult, CycleSummaryView]:
        command = RequestOnDemandCycleCommand(flow_id)
        return answer_of(lambda: CycleSummaryView.of(use_cases().request_on_demand_cycle.execute(command)))

    @server.tool(description="Riprende le aperture sospese per perdita massima.", annotations=CHANGING)
    def resume_flow_openings(flow_id: UUID) -> Annotated[CallToolResult, OpeningsResumedView]:
        def resume() -> OpeningsResumedView:
            use_cases().resume_flow_openings.execute(ResumeFlowOpeningsCommand(FlowId(flow_id)))
            return OpeningsResumedView(str(flow_id))

        return answer_of(resume)


def _install_capital_tools(server: MCPServer, use_cases: Callable[[], McpUseCases]) -> None:
    @server.tool(
        description=(
            "Incassa i profitti del flusso chiudendone le posizioni; capital è il capitale che il flusso tiene dopo "
            "l'incasso, senza valore resta quello assegnato ora."
        ),
        annotations=TRADING,
    )
    def cash_out_profits(flow_id: UUID, capital: Decimal | None = None) -> Annotated[CallToolResult, CashOutView]:
        def cash_out() -> CashOutView:
            command = CashOutProfitsCommand(FlowId(flow_id), request_identity().user_id, capital)
            return CashOutView.of(use_cases().cash_out_profits.execute(command))

        return answer_of(cash_out)

    @server.tool(description="Cambia il capitale assegnato al flusso.", annotations=CHANGING)
    def change_allocated_capital(flow_id: UUID, allocated_capital: Decimal) -> Annotated[CallToolResult, FlowView]:
        def change() -> FlowView:
            command = ChangeAllocatedCapitalCommand(FlowId(flow_id), allocated_capital, request_identity().user_id)
            return FlowView.of(use_cases().change_allocated_capital.execute(command))

        return answer_of(change)
