"""Indexes for the histories queried with a filter, newest first by keyset on instant and key.

R2.5.1, ADR 0138.

Revision ID: 0022
Revises: 0021
"""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

# The pages read the rows of the tenant, of one flow or of all of them, from the most recent instant (ADR 0138).
INDEXES = (
    ("cycles_of_tenant", "cycles", ["tenant_id", "planned_at DESC", "flow_id DESC"]),
    ("closed_positions_of_flow_newest", "closed_positions", ["tenant_id", "flow_id", "closed_at DESC", "id DESC"]),
    ("closed_positions_of_tenant", "closed_positions", ["tenant_id", "closed_at DESC", "id DESC"]),
    ("orders_of_flow", "orders", ["tenant_id", "flow_id", "created_at DESC", "id DESC"]),
    ("orders_of_tenant", "orders", ["tenant_id", "created_at DESC", "id DESC"]),
    ("account_fills_of_order", "account_fills", ["tenant_id", "order_id"]),
    ("flow_versions_in_force", "flow_versions", ["flow_id", "created_at"]),
)


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, [sa.text(column) for column in columns])


def downgrade() -> None:
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
