"""The cycle of a flow as the worker composes it, on the ports the tests give each tenant (ADR 0042, ADR 0104).

It mirrors bootstrap.cycle_of on the fake adapters: the scenarios replace one port of a tenant at a time.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from autotrading.adapters.outbound.json.cycle_journal import JsonCycleJournalAdapter
from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.application.agent.ask_agent import AskAgentUseCase
from autotrading.application.agent.ask_flow_agent import AskFlowAgentUseCase
from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.application.agent.model_gateways import ModelGateways
from autotrading.application.agent.ports import ProviderKeyOpenerPort, ProviderKeyRepositoryPort
from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.compose_cycle_context import ComposeCycleContextUseCase
from autotrading.application.flows.cycle_graph import CycleGraph, CycleSteps, GraphCheckpoints
from autotrading.application.flows.decide_cycle import DecideCycleUseCase
from autotrading.application.flows.end_cycle_flow import EndCycleFlowUseCase
from autotrading.application.flows.notify_cycle_failure import NotifyCycleFailureUseCase
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsUseCase
from autotrading.application.flows.ports import (
    AutomaticPausePort,
    ClockPort,
    ClosedPositionRepositoryPort,
    CycleContext,
    CycleDecisions,
    CycleRepositoryPort,
    ExchangeLimitsPort,
    FlowLockPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    PlannedFlowsPort,
)
from autotrading.application.flows.read_cycle_source import ReadCycleSourceUseCase
from autotrading.application.flows.record_cycle_equity import RecordCycleEquityUseCase
from autotrading.application.flows.review_cycle_risk import ReviewCycleRiskUseCase
from autotrading.application.flows.run_cycle import CycleGuards, RunCycleUseCase
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.application.flows.start_cycle_flow import StartCycleFlowUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.orders.follow_flow_orders import FollowFlowOrdersUseCase
from autotrading.application.sources.collect_cycle_source import CollectCycleSourceUseCase, SourceSystems
from autotrading.application.sources.ports import (
    ForecastRepositoryPort,
    MarketDataPort,
    NewsPort,
    PriceForecasterPort,
    PriceHistoryPort,
    SampleRepositoryPort,
    SentimentPort,
)
from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand
from autotrading.application.sources.record_actual_prices_of_tenants import RecordActualPricesOfTenantsUseCase
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.sources.source_catalog import SOURCE_CATALOG
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class TenantCyclePorts:
    """The adapters a cycle uses, bound to the tenant of its flow."""

    flows: FlowRepositoryPort
    pause: AutomaticPausePort
    start_cycle: StartCycleFlowUseCase
    end_cycle: EndCycleFlowUseCase
    provider_keys: ProviderKeyRepositoryPort
    forecasts: ForecastRepositoryPort
    samples: SampleRepositoryPort
    send_orders: SendCycleOrdersUseCase
    openings: FlowOpeningsPort
    closed_positions: ClosedPositionRepositoryPort
    follow_flow_orders: FollowFlowOrdersUseCase
    flow_paused_notice: NotifyFlowPausedUseCase
    cycle_failure: NotifyCycleFailureUseCase
    notify: NotifyUseCase
    settlement_currency: str
    checkpoints: GraphCheckpoints
    equity: RecordCycleEquityUseCase


@dataclass(frozen=True, slots=True)
class CycleServices:
    """What every cycle shares, whatever the tenant: the clock, the models, the sources, the exchanges."""

    clock: ClockPort
    model_gateways: ModelGateways
    provider_key_opener: ProviderKeyOpenerPort
    sentiments: Mapping[str, SentimentPort]
    news: NewsPort
    prices: PriceHistoryPort
    forecaster: PriceForecasterPort
    market: MarketDataPort
    exchange_limits: Mapping[str, ExchangeLimitsPort]
    environment: str


type SourcesData = tuple[SourceData, ...]


type WorkerCycle = RunCycleUseCase[CycleFlow, SourcesData, CycleContext, CycleDecisions, CycleOrder, object]
type CyclePortsOf = Callable[[TenantId], TenantCyclePorts]


def run_cycle_for(
    ports_of: CyclePortsOf,
    services: CycleServices,
    cycles_of: Callable[[TenantId], CycleRepositoryPort],
    lock: FlowLockPort,
    tenant_id: TenantId,
) -> WorkerCycle:
    """The cycle of a flow of the tenant, every node on the adapters of that tenant (ADR 0042, ADR 0104)."""
    ports = ports_of(tenant_id)
    steps = CycleSteps(
        start=ports.start_cycle,
        sources=ReadCycleSourceUseCase(
            CollectCycleSourceUseCase(
                SOURCE_CATALOG,
                SourceSystems(
                    services.sentiments, services.news, services.prices, services.forecaster, services.market
                ),
                ports.forecasts,
                ports.samples,
            ),
            services.clock,
        ),
        calls=ThreadPoolConcurrentCallsAdapter(),
        context=ComposeCycleContextUseCase(ComposeAgentContextUseCase(), services.clock),
        agent=DecideCycleUseCase(
            AskFlowAgentUseCase(
                ComposeAgentContextUseCase(),
                AskAgentUseCase(services.model_gateways, ports.provider_keys, services.provider_key_opener),
            )
        ),
        risk=ReviewCycleRiskUseCase(CheckRiskUseCase(services.exchange_limits)),
        orders=ports.send_orders,
        end=ports.end_cycle,
        journal=JsonCycleJournalAdapter(services.environment),
    )
    cycles = cycles_of(tenant_id)
    guards = CycleGuards(
        cycles=cycles,
        lock=lock,
        pause=PauseAffectedFlowsUseCase(ports.flows, ports.pause, ports.flow_paused_notice),
        clock=services.clock,
        failures=ports.cycle_failure,
    )
    return RunCycleUseCase(CycleGraph(steps, cycles, ports.checkpoints), guards, ports.equity)


def record_actual_prices(planned: PlannedFlowsPort, ports_of: CyclePortsOf, services: CycleServices) -> None:
    """The actual price beside every expired forecast of the tenants the worker plans for (R1.3.5)."""
    record = RecordActualPricesOfTenantsUseCase(
        services.prices, planned.tenants, lambda tenant_id: ports_of(tenant_id).forecasts
    )
    record.execute(RecordActualPricesCommand(services.clock.now()))
