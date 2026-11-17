"""The translations of the state of a flow for its notifications, without the database (ADR
stato-del-flusso-in-ogni-notifica).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.flow_status import (
    SqlAlchemyFlowStatusAdapter,
    cashed_out_query,
    figures_of,
    flow_query,
    last_equity_query,
    open_positions_query,
    recorded_of,
)
from autotrading.application.notifications.errors import FlowStatusUnavailableError
from autotrading.domain.notifications.flow_status import FlowStatusFigures, NotifiedFlowStatus, RecordedEquity
from autotrading.domain.tenancy.tenant_id import TenantId

PLANNED_AT = datetime(2026, 11, 17, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    ("stored", "status"),
    [
        ("active", NotifiedFlowStatus.ACTIVE),
        ("paused", NotifiedFlowStatus.PAUSED),
        ("stopped", NotifiedFlowStatus.STOPPED),
        ("draft", NotifiedFlowStatus.DRAFT),
    ],
)
def test_the_state_stored_on_the_flow_reads_in_the_words_of_the_dashboard(
    stored: str, status: NotifiedFlowStatus
) -> None:
    recorded = RecordedEquity(Decimal("312.40"), Decimal(300), Decimal(0))

    figures = figures_of({"id": uuid4(), "status": stored}, 2, "USDC", recorded)

    assert figures == FlowStatusFigures(status, 2, "USDC", recorded)


def test_the_last_equity_reads_with_the_capital_it_was_recorded_with_and_the_profits_cashed_out() -> None:
    row = {"planned_at": PLANNED_AT, "equity": Decimal("312.40"), "allocated_capital": Decimal(300)}

    assert recorded_of(row, Decimal(18)) == RecordedEquity(Decimal("312.40"), Decimal(300), Decimal(18))


def test_the_flow_is_the_one_not_archived_with_the_name() -> None:
    params = flow_query("alfa").compile().params

    assert params == {"name_1": "alfa", "status_1": "archived"}


def test_the_equity_is_the_last_one_recorded_for_the_flow() -> None:
    flow_id = uuid4()
    query = last_equity_query(flow_id)

    assert query.compile().params == {"flow_id_1": flow_id, "param_1": 1}
    assert "ORDER BY equity_snapshots.planned_at DESC" in str(query)


def test_the_profits_cashed_out_count_up_to_the_cycle_of_the_equity() -> None:
    flow_id = uuid4()

    params = cashed_out_query(flow_id, PLANNED_AT).compile().params

    assert params == {"coalesce_2": 0, "flow_id_1": flow_id, "changed_at_1": PLANNED_AT}


def test_the_open_positions_are_the_assets_the_ledger_expects_held() -> None:
    flow_id = uuid4()

    params = open_positions_query(flow_id).compile().params

    assert params == {"flow_id_1": flow_id, "size_1": 0}


def test_a_database_out_of_reach_is_the_error_of_the_port() -> None:
    engine = create_engine(
        "postgresql+psycopg://autotrading_app:unused@127.0.0.1:1/autotrading", connect_args={"connect_timeout": 1}
    )
    adapter = SqlAlchemyFlowStatusAdapter(engine, TenantId.new(), "USDC")

    with pytest.raises(FlowStatusUnavailableError, match=r"^stato del flusso non disponibile$"):
        adapter.status_of("alfa")
