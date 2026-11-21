"""The closings of the flows recorded without their flow go back to the flow they closed, with its executions.

Bug 684, ADR riparazione-delle-chiusure-attribuite-a-un-altro-flusso. Before ADR
chiusure-dei-flussi-con-il-flusso-nell-ordine the closings of a stop, a cash-out and an emergency closing were recorded
as manual commands without a flow, and the ledger gave their executions to the flow holding the asset when it read
them, possibly another flow. The closing of a flow is told apart by the data alone: a reduce-only manual order without
a flow that a closed position of the same tenant, account and asset closed, for one of those reasons, at the instant
the order executed. An order that matches more than one closed position stays as it is.

Revision ID: 0055
Revises: 0054
"""

from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None

TABLES = (
    "orders",
    "closed_positions",
    "flows",
    "account_fills",
    "account_funding",
    "flow_totals",
    "flow_position_totals",
)
# The reasons are those of the closings of a flow at a command of its user (stop, cash-out, emergency), as the history
# of the closed positions records them.
CLOSINGS_OF_FLOWS = """
INSERT INTO repaired_flow_closings (order_id, tenant_id, flow_id)
SELECT orders.id, orders.tenant_id, (array_agg(closed_positions.flow_id))[1]
FROM orders
JOIN closed_positions
    ON closed_positions.tenant_id = orders.tenant_id
    AND closed_positions.asset = orders.coin
    AND closed_positions.closed_at = orders.executed_at
    AND closed_positions.reason IN ('flow_stop', 'cash_out', 'emergency')
JOIN flows
    ON flows.id = closed_positions.flow_id
    AND flows.tenant_id = closed_positions.tenant_id
    AND flows.account_id = orders.account_id
WHERE orders.origin = 'MANUAL' AND orders.flow_id IS NULL AND orders.reduce_only
GROUP BY orders.id, orders.tenant_id
HAVING count(*) = 1
"""

# Both the flow that had the executions and the one they go back to: their totals change.
TOUCHED_FLOWS = """
INSERT INTO repaired_flows (flow_id, tenant_id)
SELECT account_fills.flow_id, account_fills.tenant_id
FROM account_fills
JOIN repaired_flow_closings
    ON repaired_flow_closings.order_id = account_fills.order_id
    AND repaired_flow_closings.tenant_id = account_fills.tenant_id
WHERE account_fills.flow_id IS NOT NULL AND account_fills.flow_id <> repaired_flow_closings.flow_id
UNION
SELECT repaired_flow_closings.flow_id, repaired_flow_closings.tenant_id
FROM repaired_flow_closings
JOIN account_fills
    ON account_fills.order_id = repaired_flow_closings.order_id
    AND account_fills.tenant_id = repaired_flow_closings.tenant_id
WHERE account_fills.flow_id IS DISTINCT FROM repaired_flow_closings.flow_id
"""

# An execution of an order of its flow, as the ledger records it (ADR 0063).
EXECUTIONS_TO_THEIR_FLOW = """
UPDATE account_fills
SET flow_id = repaired_flow_closings.flow_id, kind = 'ordine_flusso'
FROM repaired_flow_closings
WHERE account_fills.order_id = repaired_flow_closings.order_id
    AND account_fills.tenant_id = repaired_flow_closings.tenant_id
    AND account_fills.flow_id IS DISTINCT FROM repaired_flow_closings.flow_id
"""

ORDERS_TO_THEIR_FLOW = """
UPDATE orders
SET flow_id = repaired_flow_closings.flow_id
FROM repaired_flow_closings
WHERE orders.id = repaired_flow_closings.order_id AND orders.tenant_id = repaired_flow_closings.tenant_id
"""

# The same sums the ledger adds row by row (ADR 0063): PnL realized and fees of the executions, funding received.
TOTALS_OF_TOUCHED_FLOWS = """
INSERT INTO flow_totals (flow_id, tenant_id, realized_pnl, fees, funding)
SELECT
    repaired_flows.flow_id,
    repaired_flows.tenant_id,
    COALESCE((SELECT sum(realized_pnl) FROM account_fills WHERE account_fills.flow_id = repaired_flows.flow_id), 0),
    COALESCE((SELECT sum(fee) FROM account_fills WHERE account_fills.flow_id = repaired_flows.flow_id), 0),
    COALESCE((SELECT sum(amount) FROM account_funding WHERE account_funding.flow_id = repaired_flows.flow_id), 0)
FROM repaired_flows
ON CONFLICT (flow_id) DO UPDATE
SET realized_pnl = EXCLUDED.realized_pnl, fees = EXCLUDED.fees, funding = EXCLUDED.funding
"""

# An asset left without executions of the flow is a position of zero, as the ledger leaves it after a closing.
POSITIONS_OF_TOUCHED_FLOWS_FROM_ZERO = """
UPDATE flow_position_totals
SET size = 0
FROM repaired_flows
WHERE flow_position_totals.flow_id = repaired_flows.flow_id
"""

POSITIONS_OF_TOUCHED_FLOWS = """
INSERT INTO flow_position_totals (flow_id, asset, tenant_id, size)
SELECT account_fills.flow_id, account_fills.asset, account_fills.tenant_id, sum(account_fills.size)
FROM account_fills
JOIN repaired_flows ON repaired_flows.flow_id = account_fills.flow_id
GROUP BY account_fills.flow_id, account_fills.asset, account_fills.tenant_id
ON CONFLICT (flow_id, asset) DO UPDATE SET size = EXCLUDED.size
"""


def upgrade() -> None:
    # Row level security forced on the tables hides every row from the owner too, without a tenant: the closings of
    # every tenant are repaired only while it is lifted, inside the transaction of the migration.
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute("CREATE TEMPORARY TABLE repaired_flow_closings (order_id uuid, tenant_id uuid, flow_id uuid)")
    op.execute("CREATE TEMPORARY TABLE repaired_flows (flow_id uuid, tenant_id uuid)")
    for statement in (
        CLOSINGS_OF_FLOWS,
        TOUCHED_FLOWS,
        EXECUTIONS_TO_THEIR_FLOW,
        ORDERS_TO_THEIR_FLOW,
        TOTALS_OF_TOUCHED_FLOWS,
        POSITIONS_OF_TOUCHED_FLOWS_FROM_ZERO,
        POSITIONS_OF_TOUCHED_FLOWS,
    ):
        op.execute(statement)
    op.execute("DROP TABLE repaired_flows")
    op.execute("DROP TABLE repaired_flow_closings")
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # The wrong attribution is not restored: the executions of a closing belong to the flow it closed.
    pass
