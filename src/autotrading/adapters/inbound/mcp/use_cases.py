from dataclasses import dataclass

from autotrading.application.accounts.list_accounts import ListAccountsUseCase
from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.cash_out_profits import CashOutProfitsUseCase
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusUseCase
from autotrading.application.flows.create_flow import CreateFlowUseCase
from autotrading.application.flows.duplicate_flow import DuplicateFlowUseCase
from autotrading.application.flows.get_flow import GetFlowUseCase
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyUseCase
from autotrading.application.flows.list_closed_positions import ListClosedPositionsUseCase
from autotrading.application.flows.list_cycles import ListCyclesUseCase
from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsUseCase
from autotrading.application.flows.modify_flow import ModifyFlowUseCase
from autotrading.application.flows.rank_flows import RankFlowsUseCase
from autotrading.application.flows.read_cycle import ReadCycleUseCase
from autotrading.application.flows.read_flow_results import ReadFlowResultsUseCase
from autotrading.application.flows.read_flow_statistics import ReadFlowStatisticsUseCase
from autotrading.application.flows.request_on_demand_cycle import RequestOnDemandCycleUseCase
from autotrading.application.flows.resume_flow_openings import ResumeFlowOpeningsUseCase
from autotrading.application.flows.stop_flow import StopFlowUseCase


@dataclass(frozen=True, slots=True)
class McpUseCases:
    """The use cases of one request that the tools call: the same instances the API builds for the tenant of the
    request, so the same rules hold. No use case that reads or changes a credential is here.
    """

    list_flow_overviews: ListFlowOverviewsUseCase
    get_flow: GetFlowUseCase
    read_flow_results: ReadFlowResultsUseCase
    list_closed_positions: ListClosedPositionsUseCase
    list_cycles: ListCyclesUseCase
    read_cycle: ReadCycleUseCase
    read_flow_statistics: ReadFlowStatisticsUseCase
    rank_flows: RankFlowsUseCase
    list_accounts: ListAccountsUseCase
    create_flow: CreateFlowUseCase
    import_flow_strategy: ImportFlowStrategyUseCase
    duplicate_flow: DuplicateFlowUseCase
    modify_flow: ModifyFlowUseCase
    change_flow_status: ChangeFlowStatusUseCase
    stop_flow: StopFlowUseCase
    archive_flow: ArchiveFlowUseCase
    cash_out_profits: CashOutProfitsUseCase
    change_allocated_capital: ChangeAllocatedCapitalUseCase
    request_on_demand_cycle: RequestOnDemandCycleUseCase
    resume_flow_openings: ResumeFlowOpeningsUseCase
