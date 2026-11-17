from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.italian_text import money_text

SEPARATOR = " · "
NO_VALUE = "valore non disponibile"


class NotifiedFlowStatus(StrEnum):
    """The state of a flow in the words the dashboard shows it with (ADR stato-del-flusso-in-ogni-notifica)."""

    DRAFT = "bozza"
    STOPPED = "fermo"
    ACTIVE = "attivo"
    PAUSED = "in pausa"
    ARCHIVED = "archiviato"


@dataclass(frozen=True, slots=True)
class RecordedEquity:
    """The equity of the last cycle recorded, with the capital allocated and the profits cashed out it is measured
    against (ADR 0120, ADR incasso-dei-profitti).
    """

    equity: Decimal
    allocated_capital: Decimal
    cashed_out: Decimal

    @property
    def pnl(self) -> Decimal:
        """The PnL since the start: the cashed-out profits left the value of the flow, not its result."""
        return self.equity - self.allocated_capital + self.cashed_out


@dataclass(frozen=True, slots=True)
class FlowStatusFigures:
    """What a notification of a flow tells of its state; a flow that never ran a cycle has no recorded equity."""

    status: NotifiedFlowStatus
    open_positions: int
    currency: str
    recorded: RecordedEquity | None


@dataclass(frozen=True, slots=True)
class FlowStatusLine:
    """The last line of every notification of a flow (R3.5.4)."""

    text: str

    @classmethod
    def of(cls, figures: FlowStatusFigures) -> FlowStatusLine:
        parts = [*_value_parts(figures), _open_positions_text(figures.open_positions), figures.status.value]
        return cls(f"Flusso: {SEPARATOR.join(parts)}")


def _value_parts(figures: FlowStatusFigures) -> list[str]:
    recorded = figures.recorded
    if recorded is None:
        return [NO_VALUE]
    sign = "+" if recorded.pnl > 0 else ""
    currency = figures.currency
    return [f"{money_text(recorded.equity)} {currency}", f"PnL {sign}{money_text(recorded.pnl)} {currency}"]


def _open_positions_text(count: int) -> str:
    if count == 0:
        return "nessuna posizione aperta"
    if count == 1:
        return "1 posizione aperta"
    return f"{count} posizioni aperte"
