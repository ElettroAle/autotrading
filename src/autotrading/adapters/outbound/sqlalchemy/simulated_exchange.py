from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, delete, func, select, update

from autotrading.adapters.outbound.sqlalchemy.tables import (
    simulated_accounts,
    simulated_fills,
    simulated_movements,
    simulated_positions,
    simulated_protections,
)
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
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import LeverageAboveMaximumError, SimulatedOrderRefusedError
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.margin_mode import MarginMode
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ActiveProtection, ProtectionOrder
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.simulation.simulated_book import SimulatedBook, SimulatedProtection
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.simulation.simulated_fill import SimulatedFill
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId

EXCHANGE_NAME = "simulato"
NETWORK_NAME = "simulato"
SETTLEMENT_CURRENCY = "USDC"
UNKNOWN_ACCOUNT_MESSAGE = "conto simulato sconosciuto"
UNKNOWN_PROTECTION_MESSAGE = "protezione non in attesa: eseguita o cancellata"


class _AccountRow(TypedDict):
    account_id: UUID
    balance: Decimal
    leverages: dict[str, int]


class _PositionRow(TypedDict):
    coin: str
    direction: str
    size: Decimal
    leverage: int
    entry_price: Decimal
    margin: Decimal
    maintenance_rate: Decimal
    mark_price: Decimal | None


class _ProtectionRow(TypedDict):
    order_id: str
    coin: str
    kind: str
    closing_direction: str
    trigger_price: Decimal
    client_order_id: UUID


class _FillRow(TypedDict):
    id: int
    exchange_order_id: str
    client_order_id: UUID | None
    coin: str
    is_buy: bool
    size: Decimal
    price: Decimal
    fee: Decimal
    realized_pnl: Decimal
    start_position: Decimal
    liquidation: bool
    executed_at: datetime


class _MovementRow(TypedDict):
    id: int
    amount: Decimal
    moved_at: datetime


@dataclass(frozen=True, slots=True)
class _RecordedFill:
    fill: SimulatedFill
    exchange_order_id: str
    client_order_id: ClientOrderId | None


class SqlAlchemySimulatedExchangeAdapter:
    """The simulated exchange: accounts with a virtual balance that live in PostgreSQL, under row level security, one
    tenant per adapter (R6.3.2, ADR exchange-simulato-con-porte-di-lettura-e-scrittura).

    No order reaches any exchange: the engine of the domain executes it on the market the use case read, and the
    account, its positions, protections and history stay in the tables of the tenant, through a restart. Every change of
    an account locks its row, so the cycles, the settlement on the real prices and a reset never interleave. The
    instant of an execution is the one of its transaction.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId, execution: SimulatedExecution) -> None:
        self._engine = engine
        self._tenant_id = tenant_id
        self._execution = execution

    # The account as the accounts context reads it (ExchangePort, VirtualBalancePort).

    def is_real(self) -> bool:
        return False

    def network_name(self) -> str:
        return NETWORK_NAME

    def credential_fields(self) -> tuple[CredentialField, ...]:
        return ()

    def reads_credential_expiry(self) -> bool:
        """Nothing expires where there is nothing to give: the registration never asks a date."""
        return True

    def credential_expiry(self, credentials: Credentials) -> date | None:  # noqa: ARG002 - no credentials to expire
        return None

    def read_state(self, credentials: Credentials) -> AccountState:
        account_id = credentials.account_id
        with self._transaction() as connection:
            book = None if account_id is None else _book_of(connection, account_id.value)
            read_at = _now(connection)
        if book is None:
            raise ExchangeRejectedCredentialsError(UNKNOWN_ACCOUNT_MESSAGE)
        account = book.account
        return AccountState(
            Balance(account.value, SETTLEMENT_CURRENCY),
            Balance(account.available_margin, SETTLEMENT_CURRENCY),
            tuple(state_position_of(position) for position in account.positions),
            read_at,
        )

    def open(self, account_id: AccountId, balance: VirtualBalance) -> None:
        with self._transaction() as connection:
            connection.execute(
                simulated_accounts.insert().values(
                    account_id=account_id.value, tenant_id=self._tenant_id.value, balance=balance.amount, leverages={}
                )
            )
            self._moved(connection, account_id.value, balance.amount)

    def reset(self, account_id: AccountId, balance: VirtualBalance) -> None:
        with self._transaction() as connection:
            book = _locked_book_of(connection, account_id.value)
            if book is None:
                raise AccountNotFoundError
            reset = book.reset(balance.amount, _now(connection))
            self._saved(connection, account_id.value, reset.book)
            for fill in reset.fills:
                self._recorded(connection, account_id.value, _RecordedFill(fill, uuid4().hex, None))
            if reset.movement:
                self._moved(connection, account_id.value, reset.movement)

    # The operations on the account as the orders context asks them (OrderExchangePort, ProtectionExchangePort).

    def position(self, access: TradingAccess, coin: str) -> HeldPosition | None:
        with self._transaction() as connection:
            book = self._required_book(connection, access)
        held = book.account.position_of(coin)
        return None if held is None else held.held

    def set_leverage(self, access: TradingAccess, coin: str, leverage: int, margin: MarginMode) -> None:  # noqa: ARG002 - every position holds isolated margin (ADR 0095)
        with self._transaction() as connection:
            account_id = _account_id_of(access)
            book = self._required_book(connection, access, locked=True)
            connection.execute(
                update(simulated_accounts)
                .where(simulated_accounts.c.account_id == account_id)
                .values(leverages=dict(book.with_leverage(coin, leverage).leverages))
            )

    def place_market_order(self, access: TradingAccess, order: MarketOrder, market: Market) -> Execution:
        with self._transaction() as connection:
            book = self._required_book(connection, access, locked=True)
            try:
                after, fill = book.executed(self._execution, market, order, _now(connection))
            except (SimulatedOrderRefusedError, LeverageAboveMaximumError) as error:
                raise ExchangeRejectedOrderError(str(error)) from error
            account_id = _account_id_of(access)
            self._saved(connection, account_id, after)
            self._recorded(connection, account_id, _RecordedFill(fill, order.id.hex, order.id))
        return Execution(fill.size, fill.price, fill.fee, fill.realized_pnl, fill.executed_at)

    def find_order(self, access: TradingAccess, order: MarketOrder) -> Execution | None:
        query = select(simulated_fills).where(
            simulated_fills.c.account_id == _account_id_of(access), simulated_fills.c.client_order_id == order.id.value
        )
        with self._transaction() as connection:
            rows = [cast("_FillRow", row) for row in connection.execute(query).mappings()]
        return execution_of(rows)

    def place(self, access: TradingAccess, order: ProtectionOrder) -> str:
        order_id = uuid4().hex
        with self._transaction() as connection:
            self._required_book(connection, access, locked=True)
            connection.execute(
                simulated_protections.insert().values(
                    order_id=order_id,
                    tenant_id=self._tenant_id.value,
                    account_id=_account_id_of(access),
                    coin=order.asset,
                    kind=order.kind.name,
                    closing_direction=order.closing_direction.value,
                    trigger_price=order.trigger_price,
                    client_order_id=order.client_order_id.value,
                )
            )
        return order_id

    def find(self, access: TradingAccess, order: ProtectionOrder) -> str | None:
        query = select(simulated_protections.c.order_id).where(
            simulated_protections.c.account_id == _account_id_of(access),
            simulated_protections.c.client_order_id == order.client_order_id.value,
        )
        with self._transaction() as connection:
            found: str | None = connection.execute(query).scalar_one_or_none()
        return found

    def cancel(self, access: TradingAccess, asset: str, order_id: str) -> None:
        statement = (
            update(simulated_protections)
            .where(
                simulated_protections.c.account_id == _account_id_of(access),
                simulated_protections.c.coin == asset,
                simulated_protections.c.order_id == order_id,
                simulated_protections.c.closed_at.is_(None),
            )
            .values(closed_at=func.now())
        )
        with self._transaction() as connection:
            cancelled = connection.execute(statement).rowcount
        if not cancelled:
            raise ExchangeRejectedOrderError(UNKNOWN_PROTECTION_MESSAGE)

    def active(self, access: TradingAccess, asset: str) -> tuple[ActiveProtection, ...]:
        with self._transaction() as connection:
            book = self._required_book(connection, access)
        return book.active(asset)

    # The settlement on the real prices (SimulatedSettlementPort).

    def open_coins(self) -> frozenset[str]:
        with self._transaction() as connection:
            coins = connection.execute(select(simulated_positions.c.coin).distinct()).scalars().all()
        return frozenset(coins)

    def settle(self, markets: Mapping[str, Market]) -> int:
        with self._transaction() as connection:
            accounts = connection.execute(select(simulated_positions.c.account_id).distinct()).scalars().all()
            return sum(self._settled(connection, account_id, markets) for account_id in accounts)

    # The account as the flows context reads it (CycleAccountReaderPort, ActivityReaderPort, TransfersReaderPort,
    # ExecutionsReaderPort): it needs no field of any credential.

    def reference_fields(self) -> frozenset[str]:
        return frozenset()

    def cycle_reading(self, access: CycleAccess) -> CycleAccount:
        account = self._flow_book(access).account
        return CycleAccount(
            SETTLEMENT_CURRENCY,
            account.available_margin,
            tuple(cycle_position_of(position) for position in account.positions),
            account.value,
        )

    def activity(self, reference: AccountReference) -> AccountActivity:
        with self._transaction() as connection:
            book = self._flow_book_in(connection, reference)
            read_at = _now(connection)
        account = book.account
        return AccountActivity(
            SETTLEMENT_CURRENCY,
            account.value,
            account.available_margin,
            tuple(account_position_of(position) for position in account.positions),
            read_at,
        )

    def transfers(self, reference: AccountReference, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        query = (
            select(simulated_movements)
            .where(simulated_movements.c.account_id == _reference_id_of(reference))
            .order_by(simulated_movements.c.moved_at, simulated_movements.c.id)
        )
        with self._transaction() as connection:
            rows = [cast("_MovementRow", row) for row in connection.execute(query).mappings()]
        transfers = (transfer_of(row) for row in rows)
        return tuple(transfer for transfer in transfers if window.contains(transfer.transferred_at))

    def since(self, reference: AccountReference, since: datetime | None) -> ExecutionsWindow:
        account_id = _reference_id_of(reference)
        fills = select(simulated_fills).where(simulated_fills.c.account_id == account_id)
        movements = select(simulated_movements).where(simulated_movements.c.account_id == account_id)
        if since is not None:
            fills = fills.where(simulated_fills.c.executed_at >= since)
            movements = movements.where(simulated_movements.c.moved_at >= since)
        with self._transaction() as connection:
            fill_rows = connection.execute(fills.order_by(simulated_fills.c.id)).mappings().all()
            movement_rows = connection.execute(movements.order_by(simulated_movements.c.id)).mappings().all()
        return ExecutionsWindow(
            executions=tuple(ledger_execution_of(cast("_FillRow", row)) for row in fill_rows),
            funding=(),
            # The simulated exchange forgets nothing of an account.
            complete=True,
            movements=tuple(movement_of(cast("_MovementRow", row)) for row in movement_rows),
        )

    def _settled(self, connection: Connection, account_id: UUID, markets: Mapping[str, Market]) -> int:
        book = _locked_book_of(connection, account_id)
        if book is None:
            return 0
        settlement = book.settled(self._execution, markets, _now(connection))
        self._saved(connection, account_id, settlement.book)
        waiting = {protection.order.client_order_id: protection.order_id for protection in book.protections}
        for settled in settlement.fills:
            order_id = uuid4().hex if settled.client_order_id is None else waiting[settled.client_order_id]
            self._recorded(connection, account_id, _RecordedFill(settled.fill, order_id, settled.client_order_id))
        return len(settlement.fills)

    def _required_book(self, connection: Connection, access: TradingAccess, *, locked: bool = False) -> SimulatedBook:
        account_id = _account_id_of(access)
        book = _locked_book_of(connection, account_id) if locked else _book_of(connection, account_id)
        if book is None:
            raise ExchangeRejectedOrderError(UNKNOWN_ACCOUNT_MESSAGE)
        return book

    def _flow_book(self, reference: AccountReference) -> SimulatedBook:
        with self._transaction() as connection:
            return self._flow_book_in(connection, reference)

    @staticmethod
    def _flow_book_in(connection: Connection, reference: AccountReference) -> SimulatedBook:
        book = _book_of(connection, _reference_id_of(reference))
        if book is None:
            raise FlowCredentialsRefusedError(UNKNOWN_ACCOUNT_MESSAGE)
        return book

    def _saved(self, connection: Connection, account_id: UUID, book: SimulatedBook) -> None:
        """The account, its leverages and positions as the book holds them; a protection not in it waits no more."""
        connection.execute(
            update(simulated_accounts)
            .where(simulated_accounts.c.account_id == account_id)
            .values(balance=book.account.balance, leverages=dict(book.leverages))
        )
        connection.execute(delete(simulated_positions).where(simulated_positions.c.account_id == account_id))
        for position in book.account.positions:
            connection.execute(
                simulated_positions.insert().values(
                    account_id=account_id, tenant_id=self._tenant_id.value, **position_row_of(position)
                )
            )
        connection.execute(
            update(simulated_protections)
            .where(
                simulated_protections.c.account_id == account_id,
                simulated_protections.c.closed_at.is_(None),
                simulated_protections.c.order_id.not_in([protection.order_id for protection in book.protections]),
            )
            .values(closed_at=func.now())
        )

    def _recorded(self, connection: Connection, account_id: UUID, recorded: _RecordedFill) -> None:
        fill = recorded.fill
        connection.execute(
            simulated_fills.insert().values(
                tenant_id=self._tenant_id.value,
                account_id=account_id,
                exchange_order_id=recorded.exchange_order_id,
                client_order_id=None if recorded.client_order_id is None else recorded.client_order_id.value,
                coin=fill.coin,
                is_buy=fill.is_buy,
                size=fill.size,
                price=fill.price,
                fee=fill.fee,
                realized_pnl=fill.realized_pnl,
                start_position=fill.start_position,
                liquidation=fill.liquidation,
                executed_at=fill.executed_at,
            )
        )

    def _moved(self, connection: Connection, account_id: UUID, amount: Decimal) -> None:
        connection.execute(
            simulated_movements.insert().values(
                tenant_id=self._tenant_id.value, account_id=account_id, amount=amount, moved_at=_now(connection)
            )
        )

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _account_id_of(access: TradingAccess) -> UUID:
    if access.account_id is None:
        raise ExchangeRejectedOrderError(UNKNOWN_ACCOUNT_MESSAGE)
    return access.account_id


def _reference_id_of(reference: AccountReference) -> UUID:
    if reference.account_id is None:
        raise FlowCredentialsRefusedError(UNKNOWN_ACCOUNT_MESSAGE)
    return reference.account_id


def _now(connection: Connection) -> datetime:
    instant: datetime = connection.execute(select(func.now())).scalar_one()
    return instant


def _book_of(connection: Connection, account_id: UUID) -> SimulatedBook | None:
    return _book_from(connection, account_id, locked=False)


def _locked_book_of(connection: Connection, account_id: UUID) -> SimulatedBook | None:
    return _book_from(connection, account_id, locked=True)


def _book_from(connection: Connection, account_id: UUID, *, locked: bool) -> SimulatedBook | None:
    query = select(simulated_accounts).where(simulated_accounts.c.account_id == account_id)
    found = connection.execute(query.with_for_update() if locked else query).mappings().first()
    if found is None:
        return None
    account = cast("_AccountRow", found)
    positions = connection.execute(
        select(simulated_positions).where(simulated_positions.c.account_id == account_id)
    ).mappings()
    protections = connection.execute(
        select(simulated_protections)
        .where(simulated_protections.c.account_id == account_id, simulated_protections.c.closed_at.is_(None))
        .order_by(simulated_protections.c.placed_at, simulated_protections.c.order_id)
    ).mappings()
    return SimulatedBook(
        SimulatedAccount(account["balance"], tuple(position_of(cast("_PositionRow", row)) for row in positions)),
        {coin: int(leverage) for coin, leverage in account["leverages"].items()},
        tuple(protection_of(cast("_ProtectionRow", row)) for row in protections),
    )


def position_of(row: _PositionRow) -> SimulatedPosition:
    return SimulatedPosition(
        coin=row["coin"],
        direction=Direction(row["direction"]),
        size=row["size"],
        leverage=row["leverage"],
        entry_price=row["entry_price"],
        margin=row["margin"],
        maintenance_rate=row["maintenance_rate"],
        mark_price=row["mark_price"],
    )


def position_row_of(position: SimulatedPosition) -> dict[str, object]:
    return {
        "coin": position.coin,
        "direction": position.direction.value,
        "size": position.size,
        "leverage": position.leverage,
        "entry_price": position.entry_price,
        "margin": position.margin,
        "maintenance_rate": position.maintenance_rate,
        "mark_price": position.mark_price,
    }


def protection_of(row: _ProtectionRow) -> SimulatedProtection:
    order = ProtectionOrder(
        row["coin"],
        ProtectionKind[row["kind"]],
        Direction(row["closing_direction"]),
        row["trigger_price"],
        ClientOrderId(row["client_order_id"]),
    )
    return SimulatedProtection(row["order_id"], order)


def execution_of(rows: list[_FillRow]) -> Execution | None:
    """The fills of one order as one execution: the sizes summed, the price their average."""
    if not rows:
        return None
    size = sum((row["size"] for row in rows), Decimal(0))
    value = sum((row["size"] * row["price"] for row in rows), Decimal(0))
    return Execution(
        filled_size=size,
        average_price=value / size,
        fee=sum((row["fee"] for row in rows), Decimal(0)),
        realized_pnl=sum((row["realized_pnl"] for row in rows), Decimal(0)),
        executed_at=max(row["executed_at"] for row in rows),
    )


def ledger_execution_of(row: _FillRow) -> LedgerExecution:
    return LedgerExecution(
        fill_id=str(row["id"]),
        exchange_order_id=row["exchange_order_id"],
        order_id=row["client_order_id"],
        asset=row["coin"],
        size=row["size"] if row["is_buy"] else -row["size"],
        price=row["price"],
        fee=row["fee"],
        realized_pnl=row["realized_pnl"],
        start_position=row["start_position"],
        liquidation=row["liquidation"],
        executed_at=row["executed_at"],
    )


def movement_of(row: _MovementRow) -> BalanceMovement:
    return BalanceMovement(str(row["id"]), row["amount"], row["moved_at"])


def transfer_of(row: _MovementRow) -> AccountTransfer:
    direction = TransferDirection.DEPOSIT if row["amount"] > 0 else TransferDirection.WITHDRAWAL
    return AccountTransfer(row["moved_at"], abs(row["amount"]), direction)


def state_position_of(position: SimulatedPosition) -> Position:
    return Position(
        position.coin,
        PositionSide(position.direction.value),
        position.size,
        position.leverage,
        position.entry_price,
        position.mark,
        position.unrealized_pnl(position.mark),
        position.liquidation_price,
    )


def cycle_position_of(position: SimulatedPosition) -> CyclePosition:
    return CyclePosition(
        position.coin,
        TradeSide(position.direction.value),
        position.size,
        position.leverage,
        position.entry_price,
        position.mark,
        position.unrealized_pnl(position.mark),
        position.liquidation_price,
    )


def account_position_of(position: SimulatedPosition) -> AccountPosition:
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
