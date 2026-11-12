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
from autotrading.application.accounts.remove_account import RemoveAccountUseCase
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsUseCase
from autotrading.application.agent.list_models import ListModelsUseCase
from autotrading.application.agent.list_provider_keys import ListProviderKeysUseCase
from autotrading.application.agent.ports import (
    ProviderKeyRepositoryPort,
    ProviderKeySealerPort,
    ProviderKeyUsagePort,
    ProviderKeyVerifierPort,
)
from autotrading.application.agent.register_provider_key import ProviderKeyServices, RegisterProviderKeyUseCase
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyUseCase
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyUseCase
from autotrading.application.cycles.list_cycles import ListCyclesUseCase
from autotrading.application.cycles.ports import CycleHistoryPort, FlowDirectoryPort
from autotrading.application.cycles.read_cycle import ReadCycleUseCase
from autotrading.application.cycles.read_flow_cost import ReadFlowCostUseCase
from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusUseCase
from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsUseCase
from autotrading.application.flows.create_flow import CreateFlowUseCase, FlowChecks
from autotrading.application.flows.free_capital import ReadFreeCapitalUseCase
from autotrading.application.flows.get_flow_version import GetFlowVersionUseCase
from autotrading.application.flows.list_closed_positions import ListClosedPositionsUseCase
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.modify_flow import ModifyFlowUseCase
from autotrading.application.flows.ports import ClosedPositionRepositoryPort, FlowRepositoryPort
from autotrading.application.notifications.get_linked_chat import GetLinkedChatUseCase
from autotrading.application.notifications.ports import LinkCodeRepositoryPort, LinkedChatRepositoryPort
from autotrading.application.notifications.request_link_code import RequestLinkCodeUseCase
from autotrading.application.notifications.unlink_chat import UnlinkChatUseCase
from autotrading.application.orders.close_position import ClosePositionUseCase
from autotrading.application.orders.ports import PositionClosingPort
from autotrading.application.sources.get_source import GetSourceUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.verification.ports import VerificationPort
from autotrading.application.verification.run_verification import RunVerificationUseCase
from autotrading.domain.agent.model_catalog import ModelCatalog
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
    verification: VerificationPort
    source_catalog: SourceCatalog
    provider_keys: ProviderKeyRepositoryPort
    provider_key_sealer: ProviderKeySealerPort
    provider_key_verifier: ProviderKeyVerifierPort
    provider_key_usage: ProviderKeyUsagePort
    model_catalog: ModelCatalog
    flows: FlowRepositoryPort
    flow_checks: FlowChecks
    link_codes: LinkCodeRepositoryPort
    linked_chats: LinkedChatRepositoryPort
    clock: Callable[[], datetime]
    closed_positions: ClosedPositionRepositoryPort
    cycle_history: CycleHistoryPort
    flow_directory: FlowDirectoryPort


@dataclass(frozen=True, slots=True)
class TenantUseCases:
    """The use cases of one request, built by bootstrap.for_tenant on adapters bound to the tenant of the request."""

    register_account: RegisterAccountUseCase
    list_accounts: ListAccountsUseCase
    get_account: GetAccountUseCase
    replace_credentials: ReplaceCredentialsUseCase
    read_account_state: ReadAccountStateUseCase
    remove_account: RemoveAccountUseCase
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
    request_link_code: RequestLinkCodeUseCase
    get_linked_chat: GetLinkedChatUseCase
    unlink_chat: UnlinkChatUseCase
    modify_flow: ModifyFlowUseCase
    get_flow_version: GetFlowVersionUseCase
    compare_flow_versions: CompareFlowVersionsUseCase
    change_flow_status: ChangeFlowStatusUseCase
    archive_flow: ArchiveFlowUseCase
    list_closed_positions: ListClosedPositionsUseCase
    list_cycles: ListCyclesUseCase
    read_cycle: ReadCycleUseCase
    read_flow_cost: ReadFlowCostUseCase

    @classmethod
    def on(cls, tenant_id: TenantId, ports: TenantPorts) -> TenantUseCases:
        accounts, sealer, exchanges = ports.accounts, ports.sealer, ports.exchanges
        keys = ports.provider_keys
        key_services = ProviderKeyServices(ports.model_catalog, ports.provider_key_verifier, ports.provider_key_sealer)
        return cls(
            register_account=RegisterAccountUseCase(tenant_id, accounts, sealer, exchanges),
            list_accounts=ListAccountsUseCase(accounts),
            get_account=GetAccountUseCase(accounts),
            replace_credentials=ReplaceCredentialsUseCase(accounts, sealer, exchanges),
            read_account_state=ReadAccountStateUseCase(accounts, ports.account_state),
            remove_account=RemoveAccountUseCase(accounts, ports.account_state),
            close_position=ClosePositionUseCase(ports.position_closing),
            run_verification=RunVerificationUseCase(ports.verification),
            list_sources=ListSourcesUseCase(ports.source_catalog),
            get_source=GetSourceUseCase(ports.source_catalog),
            register_provider_key=RegisterProviderKeyUseCase(tenant_id, keys, key_services),
            replace_provider_key=ReplaceProviderKeyUseCase(keys, key_services),
            remove_provider_key=RemoveProviderKeyUseCase(keys, ports.provider_key_usage),
            list_provider_keys=ListProviderKeysUseCase(keys),
            list_models=ListModelsUseCase(ports.model_catalog, keys),
            create_flow=CreateFlowUseCase(tenant_id, ports.flows, ports.flow_checks),
            list_flows=ListFlowsUseCase(ports.flows),
            read_free_capital=ReadFreeCapitalUseCase(ports.flows, ports.flow_checks.accounts),
            request_link_code=RequestLinkCodeUseCase(tenant_id, ports.link_codes, ports.clock),
            get_linked_chat=GetLinkedChatUseCase(ports.linked_chats),
            unlink_chat=UnlinkChatUseCase(ports.linked_chats),
            modify_flow=ModifyFlowUseCase(ports.flows, ports.flow_checks),
            get_flow_version=GetFlowVersionUseCase(ports.flows),
            compare_flow_versions=CompareFlowVersionsUseCase(ports.flows),
            change_flow_status=ChangeFlowStatusUseCase(ports.flows),
            archive_flow=ArchiveFlowUseCase(ports.flows),
            list_closed_positions=ListClosedPositionsUseCase(ports.flows, ports.closed_positions),
            list_cycles=ListCyclesUseCase(ports.flow_directory, ports.cycle_history),
            read_cycle=ReadCycleUseCase(ports.flow_directory, ports.cycle_history),
            read_flow_cost=ReadFlowCostUseCase(ports.flow_directory, ports.cycle_history),
        )
