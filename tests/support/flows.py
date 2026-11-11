"""Flows and catalogs as the tests of the flows context build them."""

from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.bootstrap import MODEL_CATALOG
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import RangeParameter
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.platform import HYPERLIQUID, Platform, new_credentials, registration

OPENROUTER_MODEL = "openrouter/deepseek-chat"
ANTHROPIC_MODEL = "anthropic/claude-sonnet"
ACCOUNT = "test-1"
BALANCE = Decimal(1000)
TEMPERATURE = RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1))


def scenario_catalog(*models: ModelDefinition) -> ModelCatalog:
    """The models the scenarios name, short as the specifications write them, beside those of the platform."""
    named = models or (
        ModelDefinition(OPENROUTER_MODEL, (TEMPERATURE,)),
        ModelDefinition(ANTHROPIC_MODEL, (TEMPERATURE,)),
    )
    return ModelCatalog((*MODEL_CATALOG.models, *named))


def a_configuration(
    *, model: str = OPENROUTER_MODEL, allocated_capital: Decimal = Decimal(100), assets: tuple[str, ...] = ("BTC",)
) -> FlowConfiguration:
    return FlowConfiguration(
        version=FIRST_VERSION,
        assets=assets,
        cycle_interval=CycleInterval.of(None),
        model=ModelSelection(model, {"temperature": Decimal(1)}),
        sources=(),
        instructions="",
        risk_limits=RiskLimits(5, Decimal(10)),
        allocated_capital=allocated_capital,
    )


def a_flow(
    tenant_id: TenantId,
    *,
    name: str = "alfa",
    status: FlowStatus = FlowStatus.STOPPED,
    account_id: UUID | None = None,
    configuration: FlowConfiguration | None = None,
) -> Flow:
    return Flow(
        FlowId.new(),
        tenant_id,
        uuid4() if account_id is None else account_id,
        FlowName(name),
        status,
        a_configuration() if configuration is None else configuration,
    )


def account_id_of(platform: Platform, user: str, name: str = ACCOUNT, balance: Decimal = BALANCE) -> UUID:
    """The account of the user with that name, registered on the exchange with the balance when still missing."""
    if not any(account.name.value == name for account in platform.accounts_of(user)):
        credentials = new_credentials()
        platform.hyperliquid.accept(credentials, amount=balance)
        platform.register_account(user, registration(name, HYPERLIQUID, credentials))
    return platform.account_named(user, name).id.value
