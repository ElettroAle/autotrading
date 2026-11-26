from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.application.accounts.errors import AccountNotFoundError, ExchangeRejectedCredentialsError
from autotrading.application.flows.errors import FlowCredentialsRefusedError
from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.accounts.virtual_balance import VirtualBalance
from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.capital_history import AccountTransfer, TransferDirection
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.ledger import BalanceMovement, ExecutionsWindow
from autotrading.domain.flows.ledger import Execution as LedgerExecution
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.errors import LeverageAboveMaximumError, SimulatedOrderRefusedError
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.margin_mode import MarginMode
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_order import ActiveProtection, ProtectionOrder
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.simulation.simulated_book import SimulatedBook, SimulatedProtection
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.simulation.simulated_fill import SimulatedFill
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId

SIMULATED = "simulato"
CURRENCY = "USDC"
UNKNOWN_ACCOUNT = "conto simulato sconosciuto"
NOT_WAITING = "protezione non in attesa: eseguita o cancellata"
STARTED_AT = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
# A tenth of a percent: what the simulation moves every price against the order.
SIMULATION_SLIPPAGE = Slippage.percent(Decimal("0.1"))


@dataclass(frozen=True, slots=True)
class RecordedFill:
    account_id: UUID
    fill_id: str
    exchange_order_id: str
    client_order_id: ClientOrderId | None
    fill: SimulatedFill


@dataclass(frozen=True, slots=True)
class RecordedMovement:
    account_id: UUID
    movement_id: str
    amount: Decimal
    moved_at: datetime


@dataclass
class SimulatedExchangeStore:
    """What the database of the simulated exchange keeps, for every tenant: each tenant sees its own accounts only, as
    with row level security. It survives the adapters built on it, as the tables survive a restart.
    """

    books: dict[UUID, tuple[TenantId, SimulatedBook]] = field(default_factory=dict)
    fills: list[RecordedFill] = field(default_factory=list)
    movements: list[RecordedMovement] = field(default_factory=list)
    # Every protection ever placed, by its client order id, with the identifier it was given.
    placed: dict[ClientOrderId, tuple[UUID, str]] = field(default_factory=dict)
    now: datetime = STARTED_AT


class InMemorySimulatedExchangeAdapter:
    """The simulated exchange of one tenant on a store in memory, with the engine of the domain: the same ports as
    SqlAlchemySimulatedExchangeAdapter (R6.3.2).
    """

    def __init__(
        self,
        store: SimulatedExchangeStore,
        tenant_id: TenantId,
        execution: SimulatedExecution | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self._tenant_id = tenant_id
        self._execution = execution or SimulatedExecution(SIMULATION_SLIPPAGE)
        self._clock = clock or (lambda: store.now)

    def is_real(self) -> bool:
        return False

    def network_name(self) -> str:
        return SIMULATED

    def credential_fields(self) -> tuple[CredentialField, ...]:
        return ()

    def reads_credential_expiry(self) -> bool:
        return True

    def credential_expiry(self, credentials: Credentials) -> date | None:  # noqa: ARG002 - nothing expires
        return None

    def read_state(self, credentials: Credentials) -> AccountState:
        book = None if credentials.account_id is None else self._book(credentials.account_id.value)
        if book is None:
            raise ExchangeRejectedCredentialsError(UNKNOWN_ACCOUNT)
        account = book.account
        return AccountState(
            Balance(account.value, CURRENCY),
            Balance(account.available_margin, CURRENCY),
            tuple(
                Position(
                    p.coin,
                    PositionSide(p.direction.value),
                    p.size,
                    p.leverage,
                    p.entry_price,
                    p.mark,
                    p.unrealized_pnl(p.mark),
                    p.liquidation_price,
                )
                for p in account.positions
            ),
            self._clock(),
        )

    def open(self, account_id: AccountId, balance: VirtualBalance) -> None:
        self.store.books[account_id.value] = (self._tenant_id, SimulatedBook(SimulatedAccount(balance.amount)))
        self._moved(account_id.value, balance.amount)

    def reset(self, account_id: AccountId, balance: VirtualBalance) -> None:
        book = self._book(account_id.value)
        if book is None:
            raise AccountNotFoundError
        reset = book.reset(balance.amount, self._clock())
        self._save(account_id.value, reset.book)
        for fill in reset.fills:
            self._record(account_id.value, fill, None)
        if reset.movement:
            self._moved(account_id.value, reset.movement)

    def book_of(self, account_id: UUID) -> SimulatedBook:
        """What the store holds of an account of the tenant, for the assertions of a test."""
        book = self._book(account_id)
        assert book is not None, "no simulated account"
        return book

    def position(self, access: TradingAccess, coin: str) -> HeldPosition | None:
        held = self._required(access).account.position_of(coin)
        return None if held is None else held.held

    def set_leverage(self, access: TradingAccess, coin: str, leverage: int, margin: MarginMode) -> None:  # noqa: ARG002 - isolated margin always
        account_id = self._account_id(access)
        self._save(account_id, self._required(access).with_leverage(coin, leverage))

    def place_market_order(self, access: TradingAccess, order: MarketOrder, market: Market) -> Execution:
        account_id = self._account_id(access)
        try:
            after, fill = self._required(access).executed(self._execution, market, order, self._clock())
        except (SimulatedOrderRefusedError, LeverageAboveMaximumError) as error:
            raise ExchangeRejectedOrderError(str(error)) from error
        self._save(account_id, after)
        self._record(account_id, fill, order.id, order.id.hex)
        return Execution(fill.size, fill.price, fill.fee, fill.realized_pnl, fill.executed_at)

    def find_order(self, access: TradingAccess, order: MarketOrder) -> Execution | None:
        account_id = self._account_id(access)
        fills = [r.fill for r in self.store.fills if r.account_id == account_id and r.client_order_id == order.id]
        if not fills:
            return None
        size = sum((fill.size for fill in fills), Decimal(0))
        return Execution(
            size,
            sum((fill.size * fill.price for fill in fills), Decimal(0)) / size,
            sum((fill.fee for fill in fills), Decimal(0)),
            sum((fill.realized_pnl for fill in fills), Decimal(0)),
            max(fill.executed_at for fill in fills),
        )

    def place(self, access: TradingAccess, order: ProtectionOrder) -> str:
        account_id = self._account_id(access)
        order_id = uuid4().hex
        self._save(account_id, self._required(access).with_protection(SimulatedProtection(order_id, order)))
        self.store.placed[order.client_order_id] = (account_id, order_id)
        return order_id

    def find(self, access: TradingAccess, order: ProtectionOrder) -> str | None:
        placed = self.store.placed.get(order.client_order_id)
        if placed is None or placed[0] != self._account_id(access):
            return None
        return placed[1]

    def cancel(self, access: TradingAccess, asset: str, order_id: str) -> None:
        book = self._required(access)
        if order_id not in {p.order_id for p in book.protections if p.order.asset == asset}:
            raise ExchangeRejectedOrderError(NOT_WAITING)
        self._save(self._account_id(access), book.without_protection(order_id))

    def active(self, access: TradingAccess, asset: str) -> tuple[ActiveProtection, ...]:
        return self._required(access).active(asset)

    def open_coins(self) -> frozenset[str]:
        return frozenset(position.coin for book in self._books().values() for position in book.account.positions)

    def settle(self, markets: Mapping[str, Market]) -> int:
        settled = 0
        for account_id, book in self._books().items():
            settlement = book.settled(self._execution, markets, self._clock())
            self._save(account_id, settlement.book)
            waiting = {p.order.client_order_id: p.order_id for p in book.protections}
            for each in settlement.fills:
                order_id = None if each.client_order_id is None else waiting[each.client_order_id]
                self._record(account_id, each.fill, each.client_order_id, order_id)
            settled += len(settlement.fills)
        return settled

    def reference_fields(self) -> frozenset[str]:
        return frozenset()

    def cycle_reading(self, access: CycleAccess) -> CycleAccount:
        account = self._flow_book(access).account
        return CycleAccount(
            CURRENCY,
            account.available_margin,
            tuple(
                CyclePosition(
                    p.coin,
                    TradeSide(p.direction.value),
                    p.size,
                    p.leverage,
                    p.entry_price,
                    p.mark,
                    p.unrealized_pnl(p.mark),
                    p.liquidation_price,
                )
                for p in account.positions
            ),
            account.value,
        )

    def activity(self, reference: AccountReference) -> AccountActivity:
        account = self._flow_book(reference).account
        return AccountActivity(
            CURRENCY,
            account.value,
            account.available_margin,
            tuple(_account_position_of(position) for position in account.positions),
            self._clock(),
        )

    def transfers(self, reference: AccountReference, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        account_id = self._reference_id(reference)
        transfers = (
            AccountTransfer(
                m.moved_at,
                abs(m.amount),
                TransferDirection.DEPOSIT if m.amount > 0 else TransferDirection.WITHDRAWAL,
            )
            for m in self.store.movements
            if m.account_id == account_id
        )
        return tuple(transfer for transfer in transfers if window.contains(transfer.transferred_at))

    def since(self, reference: AccountReference, since: datetime | None) -> ExecutionsWindow:
        account_id = self._reference_id(reference)
        start = since or datetime.min.replace(tzinfo=UTC)
        return ExecutionsWindow(
            executions=tuple(
                _ledger_execution_of(r)
                for r in self.store.fills
                if r.account_id == account_id and r.fill.executed_at >= start
            ),
            funding=(),
            complete=True,
            movements=tuple(
                BalanceMovement(m.movement_id, m.amount, m.moved_at)
                for m in self.store.movements
                if m.account_id == account_id and m.moved_at >= start
            ),
        )

    def _books(self) -> dict[UUID, SimulatedBook]:
        return {
            account_id: book for account_id, (tenant, book) in self.store.books.items() if tenant == self._tenant_id
        }

    def _book(self, account_id: UUID) -> SimulatedBook | None:
        return self._books().get(account_id)

    def _account_id(self, access: TradingAccess) -> UUID:
        if access.account_id is None or self._book(access.account_id) is None:
            raise ExchangeRejectedOrderError(UNKNOWN_ACCOUNT)
        return access.account_id

    def _required(self, access: TradingAccess) -> SimulatedBook:
        return self.book_of(self._account_id(access))

    def _reference_id(self, reference: AccountReference) -> UUID:
        if reference.account_id is None or self._book(reference.account_id) is None:
            raise FlowCredentialsRefusedError(UNKNOWN_ACCOUNT)
        return reference.account_id

    def _flow_book(self, reference: AccountReference) -> SimulatedBook:
        return self.book_of(self._reference_id(reference))

    def _save(self, account_id: UUID, book: SimulatedBook) -> None:
        self.store.books[account_id] = (self._tenant_id, book)

    def _record(
        self, account_id: UUID, fill: SimulatedFill, client_order_id: ClientOrderId | None, order_id: str | None = None
    ) -> None:
        fill_id = str(len(self.store.fills) + 1)
        self.store.fills.append(RecordedFill(account_id, fill_id, order_id or uuid4().hex, client_order_id, fill))

    def _moved(self, account_id: UUID, amount: Decimal) -> None:
        movement_id = str(len(self.store.movements) + 1)
        self.store.movements.append(RecordedMovement(account_id, movement_id, amount, self._clock()))


def _account_position_of(position: SimulatedPosition) -> AccountPosition:
    return AccountPosition(
        asset=position.coin,
        side=TradeSide(position.direction.value),
        size=position.size,
        margin=position.margin,
        unrealized_pnl=position.unrealized_pnl(position.mark),
        leverage=position.leverage,
        entry_price=position.entry_price,
        mark_price=position.mark,
    )


def _ledger_execution_of(recorded: RecordedFill) -> LedgerExecution:
    fill = recorded.fill
    return LedgerExecution(
        fill_id=recorded.fill_id,
        exchange_order_id=recorded.exchange_order_id,
        order_id=None if recorded.client_order_id is None else recorded.client_order_id.value,
        asset=fill.coin,
        size=fill.signed_size,
        price=fill.price,
        fee=fill.fee,
        realized_pnl=fill.realized_pnl,
        start_position=fill.start_position,
        liquidation=fill.liquidation,
        executed_at=fill.executed_at,
    )
