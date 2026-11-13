from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.accounts.get_account import GetAccountUseCase
from autotrading.application.accounts.list_accounts import ListAccountsUseCase
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
    AccountStatePort,
    CredentialSealerPort,
    ExchangePort,
)
from autotrading.application.accounts.read_account_state import ReadAccountStateUseCase
from autotrading.application.accounts.register_account import RegisterAccountUseCase
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsUseCase
from autotrading.application.agent.list_models import ListModelsUseCase
from autotrading.application.agent.list_provider_keys import ListProviderKeysUseCase
from autotrading.application.agent.model_gateways import ModelGateways
from autotrading.application.agent.ports import (
    ProviderKeyRepositoryPort,
    ProviderKeySealerPort,
    ProviderKeyUsagePort,
)
from autotrading.application.agent.register_provider_key import ProviderKeyServices, RegisterProviderKeyUseCase
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyUseCase
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyUseCase
from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusUseCase
from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsUseCase
from autotrading.application.flows.create_flow import CreateFlowUseCase, FlowChecks
from autotrading.application.flows.export_account_operations import ExportAccountOperationsUseCase
from autotrading.application.flows.export_flow_operations import ExportFlowOperationsUseCase
from autotrading.application.flows.get_flow_version import GetFlowVersionUseCase
from autotrading.application.flows.list_account_operations import ListAccountOperationsUseCase
from autotrading.application.flows.list_capital_changes import ListCapitalChangesUseCase
from autotrading.application.flows.list_closed_positions import ListClosedPositionsUseCase
from autotrading.application.flows.list_cycles import ListCyclesUseCase
from autotrading.application.flows.list_flow_operations import ListFlowOperationsUseCase
from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsUseCase
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.modify_flow import ModifyFlowUseCase
from autotrading.application.flows.ports import (
    AccountActivityPort,
    AccountRemovalPorts,
    ClosedPositionRepositoryPort,
    CycleHistoryPort,
    FlowDirectoryPort,
    FlowLedgerPort,
    FlowOperationsPort,
    FlowPositionsPort,
    FlowRepositoryPort,
    FlowSummaryPort,
    RunningVerificationsPort,
)
from autotrading.application.flows.read_cycle import ReadCycleUseCase
from autotrading.application.flows.read_flow_cost import ReadFlowCostUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.read_free_capital import ReadFreeCapitalUseCase
from autotrading.application.flows.remove_account_with_flows import RemoveAccountWithFlowsUseCase
from autotrading.application.flows.stop_flow import StopFlowUseCase, StopPorts
from autotrading.application.notifications.get_linked_chat import GetLinkedChatUseCase
from autotrading.application.notifications.ports import (
    BotStartLinkPort,
    LinkCodeRepositoryPort,
    LinkedChatRepositoryPort,
)
from autotrading.application.notifications.request_link_code import RequestLinkCodeUseCase
from autotrading.application.notifications.unlink_chat import UnlinkChatUseCase
from autotrading.application.orders.close_position import ClosePositionUseCase
from autotrading.application.orders.ports import ManualClosingRecorderPort, PositionClosingPort
from autotrading.application.sources.get_source import GetSourceUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.verification.ports import VerificationPort
from autotrading.application.verification.run_verification import RunVerificationUseCase
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class TenantPorts:
    """The adapters of one request, bound to its tenant, that the use cases of the API run on."""

    accounts: AccountRepositoryPort
    sealer: CredentialSealerPort
    exchanges: Mapping[str, ExchangePort]
    account_state: AccountStatePort
    position_closing: PositionClosingPort
    manual_closings: ManualClosingRecorderPort
    verification: VerificationPort
    source_catalog: SourceCatalog
    provider_keys: ProviderKeyRepositoryPort
    provider_key_sealer: ProviderKeySealerPort
    provider_key_usage: ProviderKeyUsagePort
    model_gateways: ModelGateways
    flows: FlowRepositoryPort
    running_verifications: RunningVerificationsPort
    flow_checks: FlowChecks
    flow_positions: FlowPositionsPort
    stop_ports: StopPorts
    account_removal: AccountRemovalPorts
    account_activity: AccountActivityPort
    flow_ledger: FlowLedgerPort
    flow_operations: FlowOperationsPort
    link_codes: LinkCodeRepositoryPort
    bot_identity: BotStartLinkPort
    linked_chats: LinkedChatRepositoryPort
    clock: Callable[[], datetime]
    closed_positions: ClosedPositionRepositoryPort
    cycle_history: CycleHistoryPort
    flow_directory: FlowDirectoryPort
    flow_summaries: FlowSummaryPort
    environment: str


@dataclass(frozen=True, slots=True)
class TenantUseCases:
    """The use cases of one request, built by bootstrap.for_tenant on adapters bound to the tenant of the request."""

    register_account: RegisterAccountUseCase
    list_accounts: ListAccountsUseCase
    get_account: GetAccountUseCase
    replace_credentials: ReplaceCredentialsUseCase
    read_account_state: ReadAccountStateUseCase
    remove_account_with_flows: RemoveAccountWithFlowsUseCase
    close_position: ClosePositionUseCase
    run_verification: RunVerificationUseCase
    list_sources: ListSourcesUseCase
    get_source: GetSourceUseCase
    register_provider_key: RegisterProviderKeyUseCase
    replace_provider_key: ReplaceProviderKeyUseCase
    remove_provider_key: RemoveProviderKeyUseCase
    list_provider_keys: ListProviderKeysUseCase
    list_models: ListModelsUseCase
    create_flow: CreateFlowUseCase
    list_flows: ListFlowsUseCase
    read_free_capital: ReadFreeCapitalUseCase
    read_flow_state: ReadFlowStateUseCase
    request_link_code: RequestLinkCodeUseCase
    get_linked_chat: GetLinkedChatUseCase
    unlink_chat: UnlinkChatUseCase
    modify_flow: ModifyFlowUseCase
    get_flow_version: GetFlowVersionUseCase
    compare_flow_versions: CompareFlowVersionsUseCase
    change_flow_status: ChangeFlowStatusUseCase
    archive_flow: ArchiveFlowUseCase
    stop_flow: StopFlowUseCase
    change_allocated_capital: ChangeAllocatedCapitalUseCase
    list_capital_changes: ListCapitalChangesUseCase
    list_closed_positions: ListClosedPositionsUseCase
    list_flow_operations: ListFlowOperationsUseCase
    list_account_operations: ListAccountOperationsUseCase
    export_flow_operations: ExportFlowOperationsUseCase
    export_account_operations: ExportAccountOperationsUseCase
    list_cycles: ListCyclesUseCase
    read_cycle: ReadCycleUseCase
    read_flow_cost: ReadFlowCostUseCase
    list_flow_overviews: ListFlowOverviewsUseCase

    @classmethod
    def on(cls, tenant_id: TenantId, ports: TenantPorts) -> TenantUseCases:
        accounts, sealer, exchanges = ports.accounts, ports.sealer, ports.exchanges
        keys = ports.provider_keys
        key_services = ProviderKeyServices(ports.model_gateways, ports.provider_key_sealer)
        return cls(
            register_account=RegisterAccountUseCase(tenant_id, accounts, sealer, exchanges),
            list_accounts=ListAccountsUseCase(accounts),
            get_account=GetAccountUseCase(accounts),
            replace_credentials=ReplaceCredentialsUseCase(accounts, sealer, exchanges),
            read_account_state=ReadAccountStateUseCase(accounts, ports.account_state),
            remove_account_with_flows=RemoveAccountWithFlowsUseCase(
                ports.flows,
                ports.account_removal,
                StopFlowUseCase(ports.flows, ports.stop_ports),
                ArchiveFlowUseCase(ports.flows),
            ),
            close_position=ClosePositionUseCase(ports.position_closing, ports.manual_closings),
            run_verification=RunVerificationUseCase(ports.verification),
            list_sources=ListSourcesUseCase(ports.source_catalog),
            get_source=GetSourceUseCase(ports.source_catalog),
            register_provider_key=RegisterProviderKeyUseCase(tenant_id, keys, key_services),
            replace_provider_key=ReplaceProviderKeyUseCase(keys, key_services),
            remove_provider_key=RemoveProviderKeyUseCase(keys, ports.provider_key_usage),
            list_provider_keys=ListProviderKeysUseCase(keys),
            list_models=ListModelsUseCase(ports.model_gateways, keys),
            create_flow=CreateFlowUseCase(tenant_id, ports.flows, ports.flow_checks),
            list_flows=ListFlowsUseCase(ports.flows),
            read_free_capital=ReadFreeCapitalUseCase(ports.flows, ports.flow_checks.accounts),
            read_flow_state=ReadFlowStateUseCase(ports.flows, ports.account_activity, ports.flow_ledger),
            request_link_code=RequestLinkCodeUseCase(tenant_id, ports.link_codes, ports.bot_identity, ports.clock),
            get_linked_chat=GetLinkedChatUseCase(ports.linked_chats),
            unlink_chat=UnlinkChatUseCase(ports.linked_chats),
            modify_flow=ModifyFlowUseCase(ports.flows, ports.flow_checks, ports.account_activity),
            get_flow_version=GetFlowVersionUseCase(ports.flows),
            compare_flow_versions=CompareFlowVersionsUseCase(ports.flows),
            change_flow_status=ChangeFlowStatusUseCase(ports.flows, ports.running_verifications),
            archive_flow=ArchiveFlowUseCase(ports.flows),
            stop_flow=StopFlowUseCase(ports.flows, ports.stop_ports),
            change_allocated_capital=ChangeAllocatedCapitalUseCase(
                ports.flows,
                ports.flow_checks.accounts,
                ReadFlowStateUseCase(ports.flows, ports.account_activity, ports.flow_ledger),
                ports.clock,
            ),
            list_capital_changes=ListCapitalChangesUseCase(ports.flows),
            list_closed_positions=ListClosedPositionsUseCase(ports.flows, ports.closed_positions),
            list_flow_operations=ListFlowOperationsUseCase(ports.flows, ports.flow_operations),
            list_account_operations=ListAccountOperationsUseCase(ports.flow_operations),
            export_flow_operations=ExportFlowOperationsUseCase(ports.flows, ports.flow_operations),
            export_account_operations=ExportAccountOperationsUseCase(ports.flow_operations),
            list_cycles=ListCyclesUseCase(ports.flow_directory, ports.cycle_history),
            read_cycle=ReadCycleUseCase(ports.flow_directory, ports.cycle_history),
            read_flow_cost=ReadFlowCostUseCase(ports.flow_directory, ports.cycle_history),
            list_flow_overviews=ListFlowOverviewsUseCase(
                ports.flow_summaries, ports.cycle_history, ports.environment, ports.clock
            ),
        )
