"""The free capital of an account read now: one reading of the account, the totals of the ledger and the profits
cashed out of the flows holding it (ADR capitale-libero-al-netto-del-valore-dei-flussi)."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.flow_account import read_free_capital
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.flow_account import FakeFlowAccountAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.activity import a_fill, a_position
from tests.support.flows import a_configuration, a_flow

CASHED_AT = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


class Bench:
    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.account_id = uuid4()
        self.flows = InMemoryFlowRepositoryAdapter(FlowStore(), self.tenant_id)
        self.accounts = FakeFlowAccountAdapter()
        self.accounts.add(self.account_id, Decimal(1000))

    def flow(
        self, name: str, *, status: FlowStatus = FlowStatus.ACTIVE, capital: str = "300", asset: str = "BTC"
    ) -> Flow:
        configuration = a_configuration(assets=(asset,), allocated_capital=Decimal(capital))
        flow = a_flow(self.tenant_id, name=name, status=status, account_id=self.account_id, configuration=configuration)
        self.flows.add(flow)
        return flow

    def earned(self, flow: Flow, pnl: str) -> None:
        fill = a_fill("SOL", uuid4(), realized_pnl=Decimal(pnl), size=Decimal(0), fill_id=flow.name.value)
        self.accounts.ledger.add(self.account_id, flow.id, fill)

    def holding(self, asset: str, unrealized_pnl: str) -> None:
        reading = self.accounts.activity.activities[self.account_id]
        position = a_position(asset, unrealized_pnl=Decimal(unrealized_pnl))
        self.accounts.activity.activities[self.account_id] = replace(reading, positions=(position,))

    def free_capital(self, flow: Flow | None = None) -> FreeCapital:
        excluding = None if flow is None else flow.id
        return read_free_capital(self.flows, self.accounts.ports(), self.account_id, excluding)


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_free_capital_takes_off_the_balance_the_total_value_of_the_flows_holding_the_account(bench: Bench) -> None:
    alfa = bench.flow("alfa")
    bench.flow("beta", capital="200", asset="ETH")
    bench.earned(alfa, "70")
    bench.holding("ETH", "-50")

    assert bench.free_capital() == FreeCapital(Decimal(480), "USDC", Decimal(520), Decimal(500))
    assert bench.accounts.activity.read == [bench.account_id]


def test_archived_flows_and_flows_of_other_accounts_hold_nothing_of_the_account(bench: Bench) -> None:
    bench.flow("alfa", status=FlowStatus.ARCHIVED)
    bench.flows.add(a_flow(bench.tenant_id, name="beta", status=FlowStatus.ACTIVE))

    assert bench.free_capital() == FreeCapital(Decimal(1000), "USDC")


def test_the_flow_left_out_holds_nothing(bench: Bench) -> None:
    alfa = bench.flow("alfa", status=FlowStatus.STOPPED)
    bench.flow("beta", asset="ETH")

    assert bench.free_capital(alfa) == FreeCapital(Decimal(700), "USDC", Decimal(300), Decimal(300))


def test_the_profits_cashed_out_are_free_again(bench: Bench) -> None:
    alfa = bench.flow("alfa", capital="500")
    bench.earned(alfa, "118")
    cash_out = CapitalChange(
        alfa.id,
        CASHED_AT,
        Decimal(500),
        Decimal(500),
        UserId("anna"),
        CapitalChangeReason.CASH_OUT,
        Decimal(118),
        value_before=Decimal(618),
        cashed_profit=Decimal(118),
    )
    bench.flows.add_capital_change(alfa, cash_out)

    assert bench.free_capital() == FreeCapital(Decimal(500), "USDC", Decimal(500), Decimal(500))


def test_an_account_that_cannot_be_read_makes_the_exchange_unavailable(bench: Bench) -> None:
    bench.accounts.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        bench.free_capital()
