"""The cycles of real flows as the worker runs them: the bridges of bootstrap on the fake adapters (ADR 0042)."""

import json
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from autotrading.adapters.outbound.hyperliquid.exchange import MARGIN_CURRENCY as HYPERLIQUID_SETTLEMENT_CURRENCY
from autotrading.adapters.outbound.threads.planned_flows import ThreadsPlannedFlowsAdapter
from autotrading.application.cycles.ports import ScheduledFlow, TenantScheduledFlow
from autotrading.application.cycles.run_cycle import CycleGuards
from autotrading.application.flows.notify_unattributable import NotifyUnattributableUseCase
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import ReconcileAccountForCycleUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.bootstrap import (
    HYPERLIQUID,
    SOURCE_CATALOG,
    ClosingNoticeByNotification,
    CycleFailureNotices,
    CycleRuntime,
    CycleServices,
    FlowPauseFromFlows,
    NotifiedClosedPositions,
    OutsideClosingsInHistory,
    TenantCyclePorts,
    record_actual_prices,
    run_due_cycles,
)
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.agent.agent_context import MessageRole
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.cycles.cycle_record import CycleRecord
from autotrading.domain.cycles.cycle_schedule import CycleSchedule
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.sources.sentiment import SENTIMENT_ALTERNATIVE_ME, SENTIMENT_COINMARKETCAP
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.closed_position_repository import InMemoryClosedPositionRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.cycles import FakeClockAdapter, InMemoryCycleRepositoryAdapter, InMemoryFlowLockAdapter
from tests.fakes.exchange_limits import FakeExchangeLimitsAdapter
from tests.fakes.flow_openings import InMemoryFlowOpeningsAdapter
from tests.fakes.flow_repository import (
    InMemoryAutomaticPauseAdapter,
    InMemoryFlowRepositoryAdapter,
    InMemoryFlowTimingAdapter,
)
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.model_call import FakeModelCallAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.provider_keys import (
    FakeProviderKeyOpenerAdapter,
    FakeProviderKeySealerAdapter,
    InMemoryProviderKeyRepositoryAdapter,
)
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.fakes.source_readers import InMemorySampleRepositoryAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter
from tests.support.flows import OPENROUTER_MODEL, scenario_catalog
from tests.support.platform import Platform, new_credentials, registration

DAY = datetime(2026, 11, 12, tzinfo=UTC)
ACCOUNT = "test-1"
BALANCE = Decimal("1234.56")
KEY = "K-FAKE-CYCLE"


def at(clock: str) -> datetime:
    hours, minutes = (int(part) for part in clock.split(":")[:2])
    return DAY.replace(hour=hours, minute=minutes)


class ImmediateCycleLauncher:
    """Runs the cycle at once in the thread of the test; a permanent error is kept for the test to read."""

    def __init__(self) -> None:
        self.raised: list[AutotradingError] = []

    def launch(self, task: Callable[[], object]) -> None:
        try:
            task()
        except AutotradingError as error:
            self.raised.append(error)


class FlowCycles:
    """The flows of the users with their cycles, run on the bridges the worker uses."""

    def __init__(self) -> None:
        self.platform = Platform()
        self.platform.model_catalog = scenario_catalog()
        self.clock = FakeClockAdapter(at("10:00"))
        self.records = InMemoryCycleRepositoryAdapter()
        self.directory = ThreadsPlannedFlowsAdapter()
        self.model = FakeModelCallAdapter()
        self.sentiments = {
            name: FakeSentimentAdapter(name) for name in (SENTIMENT_ALTERNATIVE_ME.name, SENTIMENT_COINMARKETCAP.name)
        }
        self.news = FakeNewsAdapter()
        self.prices = FakePriceHistoryAdapter()
        self.market = FakeMarketDataAdapter()
        self.forecasts: dict[TenantId, InMemoryForecastRepositoryAdapter] = {}
        self.samples: dict[TenantId, InMemorySampleRepositoryAdapter] = {}
        self.limits = FakeExchangeLimitsAdapter()
        self.launcher = ImmediateCycleLauncher()
        self.credentials: dict[tuple[TenantId, str], Credentials] = {}
        self.users: dict[str, str] = {}
        self.running: threading.Thread | None = None
        self.readings = InMemoryReconciliationRepositoryAdapter()

    # The platform

    def ports_of(self, tenant_id: TenantId) -> TenantCyclePorts:
        platform = self.platform
        worker = platform.worker_for(tenant_id)
        accounts = InMemoryAccountRepositoryAdapter(platform.accounts, tenant_id)
        opener = FakeCredentialOpenerAdapter(platform.vault)
        access = OpenTradingAccessUseCase(accounts, opener)
        flows = InMemoryFlowRepositoryAdapter(platform.flows, tenant_id)
        openings = InMemoryFlowOpeningsAdapter(platform.orders_of(tenant_id))
        notify = platform.worker_for(tenant_id).notify
        closed_positions = NotifiedClosedPositions(
            InMemoryClosedPositionRepositoryAdapter(platform.closed_positions, tenant_id),
            flows,
            notify,
            HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        closing_notice = ClosingNoticeByNotification(notify, HYPERLIQUID_SETTLEMENT_CURRENCY)
        activity = ReadAccountActivityUseCase(accounts, opener, {HYPERLIQUID: platform.activity_reader})
        record_executions = RecordAccountExecutionsUseCase(
            flows,
            ReadAccountExecutionsUseCase(accounts, opener, {HYPERLIQUID: platform.activity_reader}),
            platform.platform_orders,
            platform.ledger,
        )
        reconcile_account = ReconcileAccountUseCase(
            flows,
            activity,
            self.readings,
            OutsideClosingsInHistory(RecordOutsideClosingUseCase(flows, openings, closed_positions, closing_notice)),
            record_executions,
        )
        return TenantCyclePorts(
            flows=flows,
            pause=InMemoryAutomaticPauseAdapter(platform.flows, tenant_id),
            accounts=accounts,
            read_exchange_state=worker.read_exchange_state,
            read_flow_state=ReadFlowStateUseCase(flows, activity, platform.ledger),
            provider_keys=InMemoryProviderKeyRepositoryAdapter(platform.provider_keys, tenant_id),
            forecasts=self.forecasts_of(tenant_id),
            samples=self.samples_of(tenant_id),
            execute_flow_orders=ExecuteFlowOrdersUseCase(
                access, {HYPERLIQUID: platform.order_exchange}, platform.orders_of(tenant_id), platform.slippage
            ),
            reconcile_for_cycle=ReconcileAccountForCycleUseCase(
                reconcile_account, NotifyUnattributableUseCase(accounts, notify, HYPERLIQUID_SETTLEMENT_CURRENCY)
            ),
            openings=openings,
            closed_positions=closed_positions,
            record_closing=RecordFlowClosingUseCase(openings, closed_positions, closing_notice),
            notify=notify,
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
            timing=InMemoryFlowTimingAdapter(platform.flows, tenant_id),
        )

    def services(self) -> CycleServices:
        return CycleServices(
            environment="dev",
            clock=self.clock,
            catalog=self.platform.model_catalog,
            provider_key_opener=FakeProviderKeyOpenerAdapter(self.platform.key_vault),
            model_call=self.model,
            sentiments=self.sentiments,
            news=self.news,
            prices=self.prices,
            market=self.market,
            exchange_limits={HYPERLIQUID: self.limits},
        )

    def samples_of(self, tenant_id: TenantId) -> InMemorySampleRepositoryAdapter:
        return self.samples.setdefault(tenant_id, InMemorySampleRepositoryAdapter())

    def forecasts_of(self, tenant_id: TenantId) -> InMemoryForecastRepositoryAdapter:
        return self.forecasts.setdefault(tenant_id, InMemoryForecastRepositoryAdapter())

    # The flows

    def account_of(self, user: str, name: str = ACCOUNT) -> UUID:
        platform = self.platform
        tenant_id = platform.tenant_of(user)
        if (tenant_id, name) not in self.credentials:
            credentials = new_credentials()
            platform.hyperliquid.accept(credentials, amount=BALANCE)
            platform.register_account(user, registration(name, HYPERLIQUID, credentials))
            self.credentials[tenant_id, name] = credentials
        return platform.account_named(user, name).id.value

    def register_key(self, tenant_id: TenantId, provider: str) -> None:
        name = ProviderName(provider)
        if any(key.provider == name for key in self.platform.provider_keys.of(tenant_id)):
            return
        sealed = FakeProviderKeySealerAdapter(tenant_id, self.platform.key_vault).seal(name, ProviderKey(KEY))
        self.platform.provider_keys.keys.append(RegisteredProviderKey(tenant_id, name, sealed))

    def add_flow(
        self,
        user: str,
        name: str,
        *,
        assets: tuple[str, ...] = ("BTC",),
        sources: tuple[str, ...] = (),
        model: str = OPENROUTER_MODEL,
        account: str = ACCOUNT,
        started: str = "10:00",
    ) -> Flow:
        tenant_id = self.platform.tenant_of(user)
        self.users[name] = user
        configuration = FlowConfiguration(
            version=FIRST_VERSION,
            assets=assets,
            cycle_interval=CycleInterval(15),
            model=ModelSelection(model, {}),
            sources=tuple(SourceSelection(source, 5, SOURCE_CATALOG.find(source).settings({})) for source in sources),
            instructions="Sei un trader",
            risk_limits=RiskLimits(5, Decimal(10)),
            allocated_capital=Decimal(100),
        )
        flow = Flow(
            FlowId.new(),
            tenant_id,
            self.account_of(user, account),
            FlowName(name),
            FlowStatus.ACTIVE,
            configuration,
        )
        self.platform.flows.flows.append(flow)
        self.register_key(tenant_id, model.partition("/")[0])
        self.platform.flows.anchors[flow.id] = at(started)
        self.platform.flows.first_starts[flow.id] = at(started)
        return flow

    def flow(self, name: str) -> Flow:
        return next(flow for flow in self.platform.flows.flows if flow.name.value == name)

    def reconfigure(self, name: str, change: Callable[[FlowConfiguration], FlowConfiguration]) -> None:
        flows = self.platform.flows.flows
        index = flows.index(self.flow(name))
        flows[index] = replace(flows[index], configuration=change(flows[index].configuration))

    def set_source_parameters(self, name: str, source: str, **parameters: int) -> None:
        def changed(configuration: FlowConfiguration) -> FlowConfiguration:
            selections = tuple(
                replace(selection, parameters={**selection.parameters, **parameters})
                if selection.name == source
                else selection
                for selection in configuration.sources
            )
            return replace(configuration, sources=selections)

        self.reconfigure(name, changed)

    def credentials_of(self, name: str, account: str = ACCOUNT) -> Credentials:
        return self.credentials[self.flow(name).tenant_id, account]

    # The cycles

    def run(self, name: str, clock: str | None = None) -> None:
        """Runs the cycle the flow has due now, as the worker would, alone among the flows."""
        if clock is not None:
            self.clock.current = at(clock)
        self.plan_round(only=name)

    def plan_round(self, only: str | None = None) -> None:
        flows = [flow for flow in self.platform.flows.flows if only is None or flow.name.value == only]

        class Scheduled:
            @staticmethod
            def active_of_every_tenant() -> list[TenantScheduledFlow]:
                return [
                    TenantScheduledFlow(
                        flow.tenant_id,
                        ScheduledFlow(flow.id.value, CycleSchedule(self.anchor_of(flow), timedelta(minutes=15))),
                    )
                    for flow in flows
                    if flow.status is FlowStatus.ACTIVE
                ]

        guards = CycleGuards(
            self.records,
            InMemoryFlowLockAdapter(),
            FlowPauseFromFlows(self.directory, self.ports_of),
            self.clock,
            CycleFailureNotices(self.directory, self.ports_of),
        )
        runtime = CycleRuntime(Scheduled(), guards, self.launcher)
        run_due_cycles(self.directory, self.ports_of, self.services(), runtime).execute()
        record_actual_prices(self.directory, self.ports_of, self.services())

    def anchor_of(self, flow: Flow) -> datetime:
        """As the trigger of the database: a flow is anchored at the instant it is first seen active (ADR 0042)."""
        anchor = self.platform.flows.anchors.setdefault(flow.id, self.clock.now())
        self.platform.flows.first_starts.setdefault(flow.id, anchor)
        return anchor

    def last_record(self, name: str) -> CycleRecord:
        flow_id = self.flow(name).id.value
        return [record for record in self.records.records if record.flow_id == flow_id][-1]

    # What the agent received

    def system_text(self) -> str:
        [system] = [message for message in self.model.calls[-1].messages if message.role is MessageRole.SYSTEM]
        return system.content

    def context(self) -> dict[str, object]:
        [user] = [message for message in self.model.calls[-1].messages if message.role is MessageRole.USER]
        document: dict[str, object] = json.loads(user.content)
        return document

    def sources_in_context(self, source: str, asset: str | None = None) -> list[dict[str, str]]:
        entries = self.context()["fonti"]
        assert isinstance(entries, list)
        return [
            entry["valori"]
            for entry in entries
            if entry["fonte"] == source and (asset is None or entry["asset"] == asset)
        ]
