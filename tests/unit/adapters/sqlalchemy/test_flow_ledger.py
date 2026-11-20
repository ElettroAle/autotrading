from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.flow_ledger import _entry_of, _funding_of
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import Execution, ExecutionKind, FundingEntry, FundingPayment, LedgerEntry

EXECUTED_AT = datetime(2026, 11, 20, 15, 26, 33, tzinfo=UTC)


def a_fill_row(flow_id: FlowId | None, kind: ExecutionKind, *, platform_order: bool) -> dict[str, object]:
    return {
        "fill_id": "65666898144-1",
        "exchange_order_id": "65666898144",
        "flow_id": None if flow_id is None else flow_id.value,
        "order_id": None,
        "kind": kind.value,
        "platform_order": platform_order,
        "asset": "BTC",
        "size": Decimal("0.01"),
        "price": Decimal(91000),
        "fee": Decimal("0.064328"),
        "realized_pnl": Decimal("4.624658"),
        "start_position": Decimal("-0.01"),
        "liquidation": False,
        "executed_at": EXECUTED_AT,
    }


def test_a_row_of_the_ledger_reads_back_as_the_execution_of_its_flow() -> None:
    flow_id = FlowId(uuid4())
    row = a_fill_row(flow_id, ExecutionKind.FLOW_ORDER, platform_order=True)

    entry = _entry_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert entry == LedgerEntry(
        Execution(
            fill_id="65666898144-1",
            exchange_order_id="65666898144",
            order_id=None,
            asset="BTC",
            size=Decimal("0.01"),
            price=Decimal(91000),
            fee=Decimal("0.064328"),
            realized_pnl=Decimal("4.624658"),
            start_position=Decimal("-0.01"),
            liquidation=False,
            executed_at=EXECUTED_AT,
        ),
        flow_id,
        ExecutionKind.FLOW_ORDER,
        platform_order=True,
    )


def test_a_row_of_no_flow_reads_back_without_a_flow() -> None:
    row = a_fill_row(None, ExecutionKind.UNATTRIBUTED, platform_order=False)

    entry = _entry_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert (entry.flow_id, entry.kind, entry.platform_order) == (None, ExecutionKind.UNATTRIBUTED, False)


def test_a_funding_row_reads_back_as_the_payment_of_its_flow() -> None:
    flow_id = FlowId(uuid4())
    row = {"flow_id": flow_id.value, "asset": "BTC", "amount": Decimal("-0.5"), "paid_at": EXECUTED_AT}

    entry = _funding_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert entry == FundingEntry(FundingPayment("BTC", Decimal("-0.5"), EXECUTED_AT), flow_id)


def test_a_funding_row_of_no_flow_reads_back_without_a_flow() -> None:
    row = {"flow_id": None, "asset": "ETH", "amount": Decimal(1), "paid_at": EXECUTED_AT}

    entry = _funding_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert entry.flow_id is None
