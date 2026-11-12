"""Orders linked to the flow, the cycle and the decision they come from.

R1.5.5, ADR 0050. Empty for the orders of the procedure of verification and of the manual commands.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

FLOW_OF_TENANT = "orders_flow_of_tenant"


def upgrade() -> None:
    op.add_column("orders", sa.Column("flow_id", sa.Uuid))
    op.add_column("orders", sa.Column("cycle_planned_at", sa.DateTime(timezone=True)))
    op.add_column("orders", sa.Column("decision_asset", sa.Text))
    # The flow of an order belongs to the tenant of the order: a foreign key is checked without row level security.
    op.create_foreign_key(FLOW_OF_TENANT, "orders", "flows", ["flow_id", "tenant_id"], ["id", "tenant_id"])


def downgrade() -> None:
    op.drop_constraint(FLOW_OF_TENANT, "orders")
    op.drop_column("orders", "decision_asset")
    op.drop_column("orders", "cycle_planned_at")
    op.drop_column("orders", "flow_id")
