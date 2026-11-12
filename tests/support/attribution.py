"""The accounts and the flows of "anna" as the scenarios of the attribution build them (F1.6).

The scenarios run on the use cases of the flows context with the fakes of their ports: the exchange shows what a
step puts on the account, and the platform orders are those a step says a flow sent.
"""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from pytest_bdd import parsers

from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.domain.flows.account_activity import AccountActivity, AccountFill, AccountPosition, BalanceMovement
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
NUMBER = r"(?P<{}>-?\d+(?:,\d+)?)"


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def step(text: str) -> parsers.StepParser:
    """A step whose {a}, {b}, {c} are numbers with a decimal comma and whose "{name}" are quoted words."""
    pattern = text
    for name in ("a", "b", "c"):
        pattern = pattern.replace("{" + name + "}", NUMBER.format(name))
    for name in ("account", "flow", "asset", "other", "reason", "status"):
        pattern = pattern.replace('"{' + name + '}"', f'"(?P<{name}>[^"]+)"')
    return parsers.re(f"^{pattern}$")


class AttributionBench:
    """The accounts of "anna" on the exchange, her flows, and what the platform recorded of them."""

    def __init__(self) -> None:
        self.store = FlowStore()
        self.accounts: dict[str, UUID] = {}
        self.exchange = FakeAccountActivityAdapter()
        self.orders = InMemoryPlatformOrdersAdapter()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.closed = InMemoryClosedPositionsAdapter()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.read_state = ReadFlowStateUseCase(flows, self.exchange, self.orders)
        self.reconcile = ReconcileAccountUseCase(flows, self.exchange, self.orders, self.readings, self.closed)
        self.state: FlowState | None = None

    def account(self, name: str, balance: Decimal = Decimal(1000)) -> UUID:
        if name not in self.accounts:
            self.accounts[name] = uuid4()
            self.exchange.activities[self.accounts[name]] = an_activity(balance=balance, available_margin=balance)
        return self.accounts[name]

    def add_flow(self, account: str, name: str, assets: tuple[str, ...], capital: Decimal = Decimal(100)) -> Flow:
        configuration = a_configuration(assets=assets, allocated_capital=capital)
        flow = a_flow(
            TENANT, name=name, status=FlowStatus.ACTIVE, account_id=self.account(account), configuration=configuration
        )
        self.store.flows.append(flow)
        return flow

    def flow(self, name: str) -> Flow:
        (flow,) = (flow for flow in self.store.flows if flow.name.value == name)
        return flow

    def activity_of(self, account_id: UUID) -> AccountActivity:
        return self.exchange.activities[account_id]

    def show(self, account_id: UUID, activity: AccountActivity) -> None:
        self.exchange.activities[account_id] = activity

    def extend(
        self,
        account_id: UUID,
        *,
        positions: tuple[AccountPosition, ...] = (),
        fills: tuple[AccountFill, ...] = (),
        movements: tuple[BalanceMovement, ...] = (),
    ) -> None:
        activity = self.activity_of(account_id)
        moved = sum((movement.amount for movement in movements), Decimal(0))
        self.show(
            account_id,
            replace(
                activity,
                balance=activity.balance + moved,
                positions=activity.positions + positions,
                fills=activity.fills + fills,
                movements=activity.movements + movements,
            ),
        )

    def previous_reading(self, account_id: UUID, open_assets: dict[str, frozenset[str]] | None = None) -> None:
        assets = {self.flow(name).id: held for name, held in (open_assets or {}).items()}
        self.readings.save_reading(AccountReading(account_id, READ_AT - timedelta(minutes=5), assets))

    def consult(self, name: str) -> None:
        self.state = self.read_state.execute(ReadFlowStateCommand(self.flow(name).id))

    def run_cycle(self, name: str) -> None:
        self.reconcile.execute(ReconcileAccountCommand(self.flow(name).id))

    def consulted(self) -> FlowState:
        assert self.state is not None
        return self.state
