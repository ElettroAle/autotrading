from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowNotFoundError
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.use_case = ReadFlowStateUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT), self.activity, self.ledger
        )

    def flow(self, *assets: str, tenant_id: TenantId = TENANT) -> Flow:
        flow = a_flow(
            tenant_id,
            account_id=ACCOUNT,
            configuration=a_configuration(assets=assets, allocated_capital=Decimal(500)),
        )
        self.store.flows.append(flow)
        return flow


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_state_of_a_flow_is_attributed_from_its_account(bench: Bench) -> None:
    alfa, beta = bench.flow("BTC"), bench.flow("ETH")
    bench.ledger.totals[alfa.id] = FlowTotals(alfa.id, Decimal(40), Decimal(2))
    bench.ledger.totals[beta.id] = FlowTotals(beta.id, Decimal(0), Decimal(9))
    bench.activity.activities[ACCOUNT] = an_activity(
        positions=(a_position("BTC", margin=Decimal(100)), a_position("ETH", margin=Decimal(50))),
    )

    state = bench.use_case.execute(ReadFlowStateCommand(alfa.id))

    assert [position.asset for position in state.positions] == ["BTC"]
    assert state.available_liquidity == Decimal(438)


def test_a_flow_without_anything_in_the_ledger_has_its_capital(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity()

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.available_liquidity == Decimal(500)


def test_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    other = bench.flow("BTC", tenant_id=TenantId(uuid4()))
    bench.activity.activities[ACCOUNT] = an_activity()

    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadFlowStateCommand(other.id))


def test_an_unknown_flow_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadFlowStateCommand(FlowId.new()))


def test_an_exchange_out_of_reach_is_reported(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity()
    bench.activity.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        bench.use_case.execute(ReadFlowStateCommand(flow.id))
