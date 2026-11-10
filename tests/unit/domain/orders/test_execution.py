from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.domain.orders.errors import EmptyExecutionError
from autotrading.domain.orders.execution import Execution

AT = datetime(2026, 11, 10, tzinfo=UTC)


def test_an_execution_keeps_what_the_exchange_read() -> None:
    execution = Execution(Decimal("0.0002"), Decimal(100030), Decimal("0.009"), Decimal("-0.5"), AT)

    assert (execution.filled_size, execution.average_price, execution.fee, execution.realized_pnl) == (
        Decimal("0.0002"),
        Decimal(100030),
        Decimal("0.009"),
        Decimal("-0.5"),
    )


@pytest.mark.parametrize("size", [Decimal(0), Decimal("-0.1")])
def test_an_execution_without_size_is_refused(size: Decimal) -> None:
    with pytest.raises(EmptyExecutionError):
        Execution(size, Decimal(1), Decimal(0), Decimal(0), AT)
