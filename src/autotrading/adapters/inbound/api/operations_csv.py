import csv
import io
from collections.abc import Iterable, Iterator

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.domain.flows.operations import Operation

NO_FLOW = "nessun flusso"
PURCHASE = "acquisto"
SALE = "vendita"
HEADER = (
    "istante",
    "flusso",
    "asset",
    "tipo",
    "lato",
    "quantità",
    "prezzo",
    "commissione",
    "PnL realizzato",
    "funding",
)


def side_of(operation: Operation) -> str | None:
    size = operation.size
    if size is None:
        return None
    return PURCHASE if size > 0 else SALE


def csv_lines(operations: Iterable[Operation]) -> Iterator[str]:
    """The export as CSV text, one line at a time, with the amounts as the API writes them (ADR 0018, ADR 0080)."""
    yield _line(HEADER)
    for operation in operations:
        yield _line(_cells(operation))


def _cells(operation: Operation) -> tuple[str, ...]:
    size, price = operation.size, operation.price
    return (
        operation.occurred_at.isoformat(),
        operation.flow or NO_FLOW,
        operation.asset,
        operation.kind,
        side_of(operation) or "",
        "" if size is None else amount_text(abs(size)),
        "" if price is None else amount_text(price),
        amount_text(operation.fee),
        amount_text(operation.realized_pnl),
        amount_text(operation.funding),
    )


def _line(cells: tuple[str, ...]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\r\n").writerow(cells)
    return buffer.getvalue()
