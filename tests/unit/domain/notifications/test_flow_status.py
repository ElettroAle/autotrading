"""ADR stato-del-flusso-in-ogni-notifica: the line of the state of the flow at the bottom of its notifications."""

from decimal import Decimal

import pytest

from autotrading.domain.notifications.flow_status import (
    FlowStatusFigures,
    FlowStatusLine,
    NotifiedFlowStatus,
    RecordedEquity,
)


def figures(
    equity: str | None = "312.40",
    *,
    allocated: str = "300",
    cashed_out: str = "0",
    open_positions: int = 2,
    status: NotifiedFlowStatus = NotifiedFlowStatus.ACTIVE,
) -> FlowStatusFigures:
    recorded = None if equity is None else RecordedEquity(Decimal(equity), Decimal(allocated), Decimal(cashed_out))
    return FlowStatusFigures(status, open_positions, "USDC", recorded)


def test_the_line_tells_value_pnl_since_the_start_open_positions_and_state() -> None:
    line = FlowStatusLine.of(figures())

    assert line.text == "Flusso: 312,40 USDC · PnL +12,40 USDC · 2 posizioni aperte · attivo"


def test_the_pnl_since_the_start_counts_the_profits_cashed_out() -> None:
    line = FlowStatusLine.of(figures("250", allocated="200", cashed_out="18"))

    assert line.text == "Flusso: 250 USDC · PnL +68 USDC · 2 posizioni aperte · attivo"


@pytest.mark.parametrize(("equity", "pnl"), [("290.5", "PnL -9,50 USDC"), ("300", "PnL 0 USDC")])
def test_a_pnl_not_above_zero_carries_no_plus(equity: str, pnl: str) -> None:
    assert f" · {pnl} · " in FlowStatusLine.of(figures(equity)).text


@pytest.mark.parametrize(
    ("open_positions", "told"), [(0, "nessuna posizione aperta"), (1, "1 posizione aperta"), (3, "3 posizioni aperte")]
)
def test_the_open_positions_read_as_the_user_reads_them(open_positions: int, told: str) -> None:
    assert f" · {told} · " in FlowStatusLine.of(figures(open_positions=open_positions)).text


@pytest.mark.parametrize(
    ("status", "word"),
    [
        (NotifiedFlowStatus.ACTIVE, "attivo"),
        (NotifiedFlowStatus.PAUSED, "in pausa"),
        (NotifiedFlowStatus.STOPPED, "fermo"),
        (NotifiedFlowStatus.ARCHIVED, "archiviato"),
        (NotifiedFlowStatus.DRAFT, "bozza"),
    ],
)
def test_the_state_reads_in_the_words_of_the_dashboard(status: NotifiedFlowStatus, word: str) -> None:
    assert FlowStatusLine.of(figures(status=status)).text.endswith(f" · {word}")


def test_a_flow_without_a_recorded_cycle_has_no_value_and_no_number_is_made_up() -> None:
    line = FlowStatusLine.of(figures(None, open_positions=0, status=NotifiedFlowStatus.STOPPED))

    assert line.text == "Flusso: valore non disponibile · nessuna posizione aperta · fermo"


def test_the_pnl_of_a_recorded_equity_is_its_gain_on_the_capital_allocated_and_the_profits_cashed_out() -> None:
    assert RecordedEquity(Decimal(250), Decimal(200), Decimal(18)).pnl == Decimal(68)
