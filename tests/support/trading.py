"""The orders of a tenant as the scenarios see them: the use cases built on the fake adapters, as the worker does."""

from dataclasses import dataclass, field
from decimal import Decimal
from secrets import token_hex
from uuid import UUID, uuid4

from autotrading.application.orders.open_position import OpenPositionCommand, OpenPositionUseCase
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.trading_access import FakeTradingAccessAdapter

HYPERLIQUID = "Hyperliquid"
VERIFICATION = OrderSource(OrderOrigin.VERIFICATION)


def new_access(exchange: str = HYPERLIQUID) -> TradingAccess:
    return TradingAccess(exchange, account_address=f"0x{token_hex(20)}", secret_key=f"0x{token_hex(32)}")


@dataclass
class Trading:
    exchange: FakeOrderExchangeAdapter = field(default_factory=FakeOrderExchangeAdapter)
    orders: InMemoryOrderRepositoryAdapter = field(default_factory=InMemoryOrderRepositoryAdapter)
    accesses: FakeTradingAccessAdapter = field(default_factory=FakeTradingAccessAdapter)
    accounts: dict[str, UUID] = field(default_factory=dict)
    slippage: Slippage = field(default_factory=Slippage.default)
    outcome: Order | AutotradingError | None = None

    def add_account(self, name: str, exchange: str = HYPERLIQUID) -> UUID:
        self.accounts[name] = uuid4()
        self.accesses.accesses[self.accounts[name]] = new_access(exchange)
        return self.accounts[name]

    def access_of(self, name: str) -> TradingAccess:
        return self.accesses.access(self.accounts[name])

    def open_position(self, command: OpenPositionCommand) -> None:
        use_case = OpenPositionUseCase(self.accesses, {HYPERLIQUID: self.exchange}, self.orders, self.slippage)
        try:
            self.outcome = use_case.execute(command)
        except AutotradingError as error:
            self.outcome = error

    def open_long(self, account: str, value: Decimal = Decimal(20), source: OrderSource = VERIFICATION) -> None:
        self.open_position(OpenPositionCommand(self.accounts[account], "BTC", Direction.LONG, 2, value, source))

    def order(self) -> Order:
        assert isinstance(self.outcome, Order), f"no order came out: {self.outcome}"
        return self.outcome

    def recorded(self) -> Order:
        return self.orders.get(self.order().id)

    def last_sent(self) -> MarketOrder:
        assert self.exchange.sent, "no order reached the exchange"
        return self.exchange.sent[-1]

    def reason(self) -> str:
        if isinstance(self.outcome, AutotradingError):
            return str(self.outcome)
        rejection = self.order().rejection
        assert rejection is not None, f"the order was not refused: {self.outcome}"
        return rejection.reason.value
