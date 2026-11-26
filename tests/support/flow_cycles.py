"""The cycles of real flows as the worker runs them: its composition on the fake adapters (ADR 0042)."""

import json
import threading
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from autotrading.adapters.outbound.hyperliquid.exchange import MARGIN_CURRENCY as HYPERLIQUID_SETTLEMENT_CURRENCY
from autotrading.adapters.outbound.process_memory.cycle_notices import (
    ProcessMemoryCycleNoticesAdapter,
    ProcessMemoryOpeningBlockedNoticeAdapter,
    ProcessMemoryOpeningReducedNoticeAdapter,
    ProcessMemoryOpeningsSuspendedNoticeAdapter,
    ProcessMemoryOrderRejectedNoticeAdapter,
    ProcessMemoryPositionClosedNoticeAdapter,
    ProcessMemoryPositionOpenedNoticeAdapter,
)
from autotrading.adapters.outbound.threads.planned_flows import ThreadsPlannedFlowsAdapter
from autotrading.application.flows.end_cycle_flow import EndCycleFlowUseCase
from autotrading.application.flows.follow_trailing_stops import (
    FollowTrailingStopsUseCase,
    StopMoves,
    WatchedPositionReadings,
)
from autotrading.application.flows.notify_cycle_failure import NotifyCycleFailureUseCase
from autotrading.application.flows.notify_unattributable import (
    NotifyUnattributableUseCase,
    UnattributableNotices,
)
from autotrading.application.flows.plan_flow_cycles import PlanFlowCyclesUseCase
from autotrading.application.flows.ports import (
    CycleJob,
    OpeningBlockedNoticePort,
    OpeningReducedNoticePort,
    OpeningsSuspendedNoticePort,
    OpenPositionRecords,
    PositionClosedNoticePort,
    ReconciliationAlarmPorts,
    ScheduledFlow,
    TenantScheduledFlow,
)
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow import CycleAccountReadings, ReadCycleFlowUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateUseCase
from autotrading.application.flows.read_flow_state import ClosingReadings, ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import ReconcileAccountForCycleUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.record_cycle_equity import RecordCycleEquityUseCase
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.record_protection_closing import RecordProtectionClosingUseCase
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.application.flows.start_cycle_flow import StartCycleFlowUseCase
from autotrading.application.flows.transient_retry import TransientRetry
from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_opening_blocked import NotifyOpeningBlockedUseCase
from autotrading.application.notifications.notify_opening_reduced import NotifyOpeningReducedUseCase
from autotrading.application.notifications.notify_openings_suspended import NotifyOpeningsSuspendedUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.notify_reconciliation_alarm import NotifyReconciliationAlarmUseCase
from autotrading.application.notifications.notify_source_credentials_rejected import (
    NotifySourceCredentialsRejectedUseCase,
)
from autotrading.application.notifications.notify_unattributable_fill import NotifyUnattributableFillUseCase
from autotrading.application.notifications.notify_unattributable_position import (
    NotifyUnattributablePositionUseCase,
)
from autotrading.application.notifications.ports import FlowStatusPort
from autotrading.application.orders.execute_cycle_orders import ExecuteCycleOrdersUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase, FlowOrderProtection
from autotrading.application.orders.follow_flow_orders import FlowOrderFollowers, FollowFlowOrdersUseCase
from autotrading.application.orders.move_flow_stop import MoveFlowStopUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.ports import OrderRejectedNoticePort, PositionOpenedNoticePort
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionUseCase
from autotrading.application.orders.protect_open_positions import ProtectOpenPositionsUseCase
from autotrading.application.orders.record_waiting_protections import RecordWaitingProtectionsUseCase
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.agent.agent_context import MessageRole
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import AdapterSelection, ModelSelection, SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.closed_position_repository import InMemoryClosedPositionRepositoryAdapter
from tests.fakes.consecutive_failures import InMemoryConsecutiveFailuresAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.cycles import (
    FakeClockAdapter,
    InMemoryCycleCheckpointsAdapter,
    InMemoryFlowLockAdapter,
)
from tests.fakes.equity_snapshots import EquitySnapshotStore, InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.exchange_limits import FakeExchangeLimitsAdapter
from tests.fakes.exit_plan_repository import InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_openings import InMemoryFlowOpeningsAdapter
from tests.fakes.flow_protection_levels import InMemoryFlowProtectionLevelsAdapter
from tests.fakes.flow_repository import (
    InMemoryAutomaticPauseAdapter,
    InMemoryFlowRepositoryAdapter,
    InMemoryFlowTimingAdapter,
)
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.key_expiries import InMemoryKeyExpiriesAdapter
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.model_call import FakeModelCallAdapter
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.model_gateway import FakeModelGatewayAdapter
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.fakes.past_decisions import InMemoryPastDecisionsAdapter
from tests.fakes.pause import FakePauseAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter
from tests.fakes.provider_keys import (
    FakeProviderKeyOpenerAdapter,
    FakeProviderKeySealerAdapter,
    InMemoryProviderKeyRepositoryAdapter,
)
from tests.fakes.social import FakeSocialAdapter
from tests.fakes.source_credentials import FakeSourceSecretsOpenerAdapter, InMemorySourceCredentialsRepositoryAdapter
from tests.fakes.source_readers import InMemorySampleRepositoryAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter
from tests.fakes.volumes import FakeVolumesAdapter
from tests.fakes.watched_positions import InMemoryWatchedPositionsAdapter
from tests.fakes.whale_transfers import FakeWhaleTransfersAdapter
from tests.support.cycle_composition import (
    CycleServices,
    TenantCyclePorts,
    WorkerCycle,
    record_actual_prices,
    run_cycle_for,
)
from tests.support.exchange_connections import connection_of
from tests.support.flows import OPENROUTER_MODEL, scenario_catalog
from tests.support.platform import HYPERLIQUID, Platform, new_credentials, registration
from tests.support.provider_key import api_key_of
from tests.support.source_selections import BEFORE_THE_ADAPTERS, reader_of

DAY = datetime(2026, 11, 12, tzinfo=UTC)
ACCOUNT = "test-1"
BALANCE = Decimal("1234.56")
KEY = "K-FAKE-CYCLE"


def at(clock: str) -> datetime:
    hours, minutes = (int(part) for part in clock.split(":")[:2])
    return DAY.replace(hour=hours, minute=minutes)


class ImmediateCycleScheduler:
    """Runs every job it keeps at once in the thread of the test; a permanent error is kept for the test to read."""

    def __init__(self) -> None:
        self.raised: list[AutotradingError] = []

    def keep(self, jobs: Sequence[CycleJob]) -> None:
        for job in jobs:
            try:
                job.run()
            except AutotradingError as error:
                self.raised.append(error)


class CycleNoticeHold:
    """The notices of a flow as the worker composes them for a cycle: held until it records its state (ADR
    notifiche-del-ciclo-dopo-lo-stato-registrato); without a cycle, told at once, as the tests that call one step read
    them."""

    def __init__(self, notices: ProcessMemoryCycleNoticesAdapter | None) -> None:
        self._notices = notices

    def opened(self, notice: PositionOpenedNoticePort) -> PositionOpenedNoticePort:
        return notice if self._notices is None else ProcessMemoryPositionOpenedNoticeAdapter(notice, self._notices)

    def rejected(self, notice: OrderRejectedNoticePort) -> OrderRejectedNoticePort:
        return notice if self._notices is None else ProcessMemoryOrderRejectedNoticeAdapter(notice, self._notices)

    def closed(self, notice: PositionClosedNoticePort) -> PositionClosedNoticePort:
        return notice if self._notices is None else ProcessMemoryPositionClosedNoticeAdapter(notice, self._notices)

    def suspended(self, notice: OpeningsSuspendedNoticePort) -> OpeningsSuspendedNoticePort:
        if self._notices is None:
            return notice
        return ProcessMemoryOpeningsSuspendedNoticeAdapter(notice, self._notices)

    def reduced(self, notice: OpeningReducedNoticePort) -> OpeningReducedNoticePort:
        return notice if self._notices is None else ProcessMemoryOpeningReducedNoticeAdapter(notice, self._notices)

    def blocked(self, notice: OpeningBlockedNoticePort) -> OpeningBlockedNoticePort:
        return notice if self._notices is None else ProcessMemoryOpeningBlockedNoticeAdapter(notice, self._notices)


class FlowCycles:
    """The flows of the users with their cycles, run as the worker composes them."""

    def __init__(self, platform: Platform | None = None) -> None:
        # The platform of the API too when a scenario hands it over: what the API does is what the cycles find.
        self.platform = platform or Platform()
        self.platform.model_catalog = scenario_catalog()
        self.clock = FakeClockAdapter(at("10:00"))
        self.checkpoints = InMemoryCycleCheckpointsAdapter()
        # The table of the cycles is one: what the worker records is what the API reads.
        self.records = self.platform.cycles
        # One lock per installation, as the advisory locks of PostgreSQL: a cycle asked for now meets the one running.
        self.lock = InMemoryFlowLockAdapter()
        self.directory = ThreadsPlannedFlowsAdapter()
        self.model = FakeModelCallAdapter()
        self.pause = FakePauseAdapter()
        # The two adapters of the sentiment, by the name each declares (R4.1.1).
        self.sentiments = {name: FakeSentimentAdapter(name) for name in ("alternative.me", "CoinMarketCap")}
        self.news = FakeNewsAdapter()
        # The providers of the large transfers a test offers, by the name each declares (R5.1.1).
        self.whales: dict[str, FakeWhaleTransfersAdapter] = {}
        # The exchanges of the volumes a test offers, by the name each declares (R5.1.2).
        self.volumes: dict[str, FakeVolumesAdapter] = {}
        # The social providers a test offers, by the name each declares (R5.1.3).
        self.socials: dict[str, FakeSocialAdapter] = {}
        self.prices = FakePriceHistoryAdapter()
        self.forecaster = FakePriceForecasterAdapter()
        self.market = FakeMarketDataAdapter()
        self.platform.source_systems = self.systems()
        self.forecasts: dict[TenantId, InMemoryForecastRepositoryAdapter] = {}
        self.samples: dict[TenantId, InMemorySampleRepositoryAdapter] = {}
        self.limits = FakeExchangeLimitsAdapter()
        self.scheduler = ImmediateCycleScheduler()
        self.credentials: dict[tuple[TenantId, str], Credentials] = {}
        self.users: dict[str, str] = {}
        self.running: threading.Thread | None = None
        self.readings = self.platform.readings
        self.equity_snapshots = EquitySnapshotStore()
        # The state of the flows their notices end with: the fake of the platform unless a scenario reads the stores.
        self.flow_status: FlowStatusPort = self.platform.flow_status
        self.platform.worker_clock = self.clock
        # Composed when a cycle is asked for: the cycle uses the worker, which holds this run.
        self.platform.cycle_run_of = lambda tenant_id: lambda command: self.run_cycle_of(tenant_id).execute(command)

    # The platform

    def ports_of(
        self, tenant_id: TenantId, notices: ProcessMemoryCycleNoticesAdapter | None = None
    ) -> TenantCyclePorts:
        platform, hold = self.platform, CycleNoticeHold(notices)
        accounts = InMemoryAccountRepositoryAdapter(platform.accounts, tenant_id)
        opener = FakeCredentialOpenerAdapter(platform.vault, platform.openings)
        access = OpenTradingAccessUseCase(accounts, opener)
        flows = InMemoryFlowRepositoryAdapter(platform.flows, tenant_id)
        openings = InMemoryFlowOpeningsAdapter(platform.orders_of(tenant_id))
        exit_plans = InMemoryExitPlanRepositoryAdapter(platform.exit_plans, tenant_id)
        notify = platform.worker_for(tenant_id).notify
        notify_flow = NotifyFlowEventUseCase(notify, self.flow_status)
        closed_positions = InMemoryClosedPositionRepositoryAdapter(platform.closed_positions, tenant_id)
        closing_notice = hold.closed(NotifyPositionClosedUseCase(notify_flow, HYPERLIQUID_SETTLEMENT_CURRENCY))
        activity = ReadAccountActivityUseCase(accounts, opener, {HYPERLIQUID: platform.activity_reader})
        protections = InMemoryProtectionRepositoryAdapter(platform.protections, tenant_id)
        protection_levels = InMemoryFlowProtectionLevelsAdapter(platform.protections, tenant_id)
        watched = InMemoryWatchedPositionsAdapter(platform.watched_positions, platform.flows, tenant_id)
        records = OpenPositionRecords(exit_plans, protection_levels, watched)
        order_exchanges = {HYPERLIQUID: connection_of(platform.order_exchange, platform.protection_exchange)}
        cancel_protections = platform.cancel_protections(tenant_id)
        record_executions = RecordAccountExecutionsUseCase(
            flows,
            ReadAccountExecutionsUseCase(accounts, opener, {HYPERLIQUID: platform.activity_reader}),
            platform.platform_orders,
            platform.ledger,
        )
        alerts = platform.alerts_of(tenant_id)
        reconcile_account = ReconcileAccountUseCase(
            flows,
            activity,
            self.readings,
            RecordOutsideClosingUseCase(
                flows, openings, closed_positions, closing_notice, exit_plans, cancel_protections
            ),
            record_executions,
            platform.ledger,
            RecordProtectionClosingUseCase(
                flows, openings, closed_positions, closing_notice, exit_plans, cancel_protections
            ),
            ReconciliationAlarmPorts(
                accounts, accounts, NotifyReconciliationAlarmUseCase(notify, alerts, HYPERLIQUID_SETTLEMENT_CURRENCY)
            ),
            alerts,
        )
        reconcile_for_cycle = ReconcileAccountForCycleUseCase(
            reconcile_account,
            NotifyUnattributableUseCase(
                accounts,
                UnattributableNotices(
                    NotifyUnattributablePositionUseCase(notify, alerts),
                    NotifyUnattributableFillUseCase(notify, alerts),
                ),
            ),
        )
        read_cycle_flow = ReadCycleFlowUseCase(
            flows,
            InMemoryFlowTimingAdapter(platform.flows, tenant_id),
            CycleAccountReadings(
                ReadCycleAccountUseCase(accounts, accounts, opener, {HYPERLIQUID: platform.hyperliquid}),
                RecordWaitingProtectionsUseCase(access, order_exchanges, protections),
            ),
            ReadCycleFlowStateUseCase(
                ReadFlowStateUseCase(
                    flows,
                    activity,
                    platform.ledger,
                    records,
                    ClosingReadings(closed_positions, self.clock.now),
                ),
                reconcile_for_cycle,
            ),
            self.readings,
        )
        retry = TransientRetry(self.pause, self.clock)
        execute_flow_orders = ExecuteFlowOrdersUseCase(
            access,
            order_exchanges,
            platform.orders_of(tenant_id),
            platform.slippage,
            FlowOrderProtection(
                ProtectFlowPositionUseCase(
                    order_exchanges, protections, platform.orders_of(tenant_id), platform.slippage
                ),
                cancel_protections,
                UpdateFlowProtectionUseCase(order_exchanges, protections),
            ),
            retry,
        )
        follow_flow_orders = FollowFlowOrdersUseCase(
            FlowOrderFollowers(
                hold.rejected(NotifyOrderRejectedUseCase(notify_flow)),
                hold.opened(NotifyPositionOpenedUseCase(notify_flow, HYPERLIQUID_SETTLEMENT_CURRENCY)),
                RecordFlowClosingUseCase(flows, openings, closed_positions, closing_notice, exit_plans),
            )
        )
        return TenantCyclePorts(
            flows=flows,
            pause=InMemoryAutomaticPauseAdapter(platform.flows, tenant_id),
            start_cycle=StartCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            end_cycle=EndCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            record_executions=record_executions,
            read_cycle_flow=read_cycle_flow,
            provider_keys=InMemoryProviderKeyRepositoryAdapter(platform.provider_keys, tenant_id),
            forecasts=self.forecasts_of(tenant_id),
            samples=self.samples_of(tenant_id),
            source_credentials=InMemorySourceCredentialsRepositoryAdapter(platform.source_credentials, tenant_id),
            source_credentials_rejected_notice=NotifySourceCredentialsRejectedUseCase(notify),
            send_orders=SendCycleOrdersUseCase(
                ExecuteCycleOrdersUseCase(
                    execute_flow_orders,
                    follow_flow_orders,
                    ProtectOpenPositionsUseCase(access, order_exchanges, protections, retry),
                ),
                openings,
                flows,
                records,
            ),
            openings=openings,
            closed_positions=closed_positions,
            follow_flow_orders=follow_flow_orders,
            flow_paused_notice=NotifyFlowPausedUseCase(notify_flow, alerts),
            cycle_failure=NotifyCycleFailureUseCase(flows, NotifyCycleFailedUseCase(notify_flow)),
            notify=notify,
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
            checkpoints=self.checkpoints,
            equity=RecordCycleEquityUseCase(InMemoryEquitySnapshotRepositoryAdapter(self.equity_snapshots, tenant_id)),
            consecutive_failures=InMemoryConsecutiveFailuresAdapter(self.records, platform.flows),
            openings_suspensions=InMemoryOpeningsSuspensionAdapter(platform.flows, tenant_id),
            loss_references=InMemoryEquitySnapshotRepositoryAdapter(self.equity_snapshots, tenant_id),
            openings_suspended_notice=hold.suspended(NotifyOpeningsSuspendedUseCase(notify_flow)),
            opening_reduced_notice=hold.reduced(
                NotifyOpeningReducedUseCase(notify_flow, HYPERLIQUID_SETTLEMENT_CURRENCY)
            ),
            opening_blocked_notice=hold.blocked(NotifyOpeningBlockedUseCase(notify_flow)),
            flow_keys=InMemoryKeyExpiriesAdapter(
                platform.accounts, platform.provider_keys, platform.flows, tenant_id, platform.source_credentials
            ),
            past_decisions=InMemoryPastDecisionsAdapter(
                self.records, platform.orders_of(tenant_id), platform.closed_positions
            ),
        )

    def trailing_stops_of(self, tenant_id: TenantId) -> FollowTrailingStopsUseCase:
        """The check of the stops that follow the price of the tenant, as the worker composes it every minute (R5.5.1,
        ADR sorveglianza-del-prezzo-per-lo-stop-che-segue): it meets the lock of the cycles."""
        platform = self.platform
        accounts = InMemoryAccountRepositoryAdapter(platform.accounts, tenant_id)
        opener = FakeCredentialOpenerAdapter(platform.vault, platform.openings)
        order_exchanges = {HYPERLIQUID: connection_of(platform.order_exchange, platform.protection_exchange)}
        retry = TransientRetry(self.pause, self.clock)
        move = MoveFlowStopUseCase(
            OpenTradingAccessUseCase(accounts, opener),
            UpdateFlowProtectionUseCase(
                order_exchanges, InMemoryProtectionRepositoryAdapter(platform.protections, tenant_id)
            ),
            retry,
        )
        return FollowTrailingStopsUseCase(
            InMemoryFlowRepositoryAdapter(platform.flows, tenant_id),
            InMemoryWatchedPositionsAdapter(platform.watched_positions, platform.flows, tenant_id),
            self.lock,
            WatchedPositionReadings(
                ReadAccountActivityUseCase(accounts, opener, {HYPERLIQUID: platform.activity_reader}),
                InMemoryFlowOpeningsAdapter(platform.orders_of(tenant_id)),
                InMemoryFlowProtectionLevelsAdapter(platform.protections, tenant_id),
            ),
            StopMoves(move, retry, self.clock),
        )

    def services(self) -> CycleServices:
        return CycleServices(
            environment="dev",
            clock=self.clock,
            model_gateways={
                "models": FakeModelGatewayAdapter(InMemoryModelCatalogAdapter(self.platform.model_catalog), self.model)
            },
            provider_key_opener=FakeProviderKeyOpenerAdapter(self.platform.key_vault, self.platform.openings),
            pause=self.pause,
            sources=self.systems(),
            source_secrets_opener=FakeSourceSecretsOpenerAdapter(self.platform.source_vault),
            exchange_limits={HYPERLIQUID: self.limits},
        )

    def systems(self) -> SourceSystems:
        return SourceSystems(
            tuple(self.sentiments.values()),
            self.news,
            self.prices,
            self.forecaster,
            self.market,
            tuple(self.whales.values()),
            tuple(self.volumes.values()),
            tuple(self.socials.values()),
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
        sealed = FakeProviderKeySealerAdapter(tenant_id, self.platform.key_vault).seal(name, api_key_of(KEY))
        key = RegisteredProviderKey(tenant_id, name, sealed)
        self.platform.provider_keys.keys.append(key)
        self.platform.provider_keys.stamp(key)

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
            sources=self.selections(sources),
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

    def set_source_parameters(self, name: str, source: str, **parameters: int | tuple[int, ...]) -> None:
        def changed(configuration: FlowConfiguration) -> FlowConfiguration:
            selections = tuple(
                replace(
                    selection,
                    adapters=tuple(
                        replace(adapter, parameters={**adapter.parameters, **parameters})
                        for adapter in selection.adapters
                    ),
                )
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
                    if flow.status.runs_cycles
                ]

        PlanFlowCyclesUseCase(Scheduled(), self.directory, self.run_cycle_of, self.scheduler, self.clock).execute()
        record_actual_prices(self.directory, self.ports_of, self.services())

    def run_cycle_of(self, tenant_id: TenantId) -> WorkerCycle:
        return run_cycle_for(self.ports_of, self.services(), lambda _tenant: self.records, self.lock, tenant_id)

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
        """The values of a source in the context; a name before the adapters means only the adapter it became."""
        entries = self.context()["fonti"]
        assert isinstance(entries, list)
        name, adapter = reader_of(source)
        return [
            entry["valori"]
            for entry in entries
            if entry["fonte"] == name
            and (source not in BEFORE_THE_ADAPTERS or entry["adapter"] == adapter)
            and (asset is None or entry["asset"] == asset)
        ]

    def selections(self, sources: tuple[str, ...]) -> tuple[SourceSelection, ...]:
        """The sources named, each with its adapter at weight 5 and the defaults of the catalog; two names of the same
        source are one source with both adapters."""
        catalog = ListSourcesUseCase(self.systems()).execute()
        adapters_of: dict[str, list[AdapterSelection]] = {}
        for source in sources:
            name, adapter = reader_of(source)
            settings = catalog.find(name).settings(adapter, {})
            adapters_of.setdefault(name, []).append(AdapterSelection(adapter, 5, settings))
        return tuple(SourceSelection(name, tuple(adapters)) for name, adapters in adapters_of.items())
