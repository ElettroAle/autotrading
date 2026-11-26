"""The fee of the account of a flow, read for its agent only with the option on (R5.5.6, ADR
costo-di-andata-e-ritorno-nel-contesto-dell-agente)."""

from dataclasses import replace
from decimal import Decimal

from autotrading.application.flows.read_round_trip_cost import ReadRoundTripCostUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.round_trip_cost import RoundTripCost
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.flows import a_configuration, a_flow
from tests.support.platform import HYPERLIQUID
from tests.support.worker import TENANT, Worker

UNREACHABLE = "exchange non raggiungibile, riprovare"


class Bench:
    def __init__(self, *, with_reader: bool = True) -> None:
        self.worker, self.reader = Worker(), FakeActivityReaderAdapter()
        self.account = self.worker.saved_account()
        self.opener = FakeCredentialOpenerAdapter(self.worker.vault)
        readers = {HYPERLIQUID: self.reader} if with_reader else {}
        accounts = InMemoryAccountRepositoryAdapter(self.worker.store, TENANT)
        self.use_case = ReadRoundTripCostUseCase(accounts, self.opener, readers)

    @property
    def address(self) -> str:
        return self.worker.vault[self.account.credentials.ciphertext][2].value("account_address")

    def flow(self, *, fees_for_agent: bool) -> Flow:
        configuration = replace(a_configuration(), fees_for_agent=fees_for_agent)
        return a_flow(TENANT, account_id=self.account.id.value, configuration=configuration)


def test_with_the_option_on_the_fee_of_the_account_is_read_on_its_address() -> None:
    bench = Bench()
    bench.reader.market_order_fee_rates[bench.address] = Decimal("0.0004")

    assert bench.use_case.execute(bench.flow(fees_for_agent=True)) == RoundTripCost.of_rate(Decimal("0.0004"))
    assert bench.reader.fee_readings == [bench.address]


def test_with_the_option_off_nothing_is_read_nor_opened() -> None:
    bench = Bench()

    assert bench.use_case.execute(bench.flow(fees_for_agent=False)) == RoundTripCost()
    assert bench.reader.fee_readings == []
    assert bench.opener.opened_addresses == []


def test_an_exchange_that_does_not_answer_leaves_the_cost_missing_with_its_reason() -> None:
    bench = Bench()
    bench.reader.market_order_fee_reachable = False

    assert bench.use_case.execute(bench.flow(fees_for_agent=True)) == RoundTripCost.unread(UNREACHABLE)


def test_an_exchange_without_a_reader_of_the_fee_leaves_the_cost_missing() -> None:
    bench = Bench(with_reader=False)

    assert bench.use_case.execute(bench.flow(fees_for_agent=True)) == RoundTripCost.unread(UNREACHABLE)
    assert bench.opener.opened_addresses == []
