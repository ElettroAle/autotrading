"""The checkpoints of the decision cycles, written by the LangGraph checkpointer, under row level security.

The tables have the schema of langgraph-checkpoint-postgres 3.x after all its migrations: the schema stays in
Alembic and the checkpointer never creates it. The tenant is the first segment of the thread of a cycle,
"<tenant>/<flow>/<planned instant>". Bug 183, ADR 0104.

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
CHECKPOINT_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")


def _thread_columns() -> list[sa.Column[str]]:
    return [
        sa.Column("thread_id", sa.Text, nullable=False),
        sa.Column("checkpoint_ns", sa.Text, nullable=False, server_default=""),
    ]


def _tenant_of_thread() -> sa.Column[str]:
    return sa.Column(
        "tenant_id",
        sa.Uuid,
        sa.ForeignKey("tenants.id"),
        sa.Computed("split_part(thread_id, '/', 1)::uuid", persisted=True),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "checkpoints",
        *_thread_columns(),
        sa.Column("checkpoint_id", sa.Text, nullable=False),
        sa.Column("parent_checkpoint_id", sa.Text),
        sa.Column("type", sa.Text),
        sa.Column("checkpoint", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        _tenant_of_thread(),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "checkpoint_id"),
    )
    op.create_table(
        "checkpoint_blobs",
        *_thread_columns(),
        sa.Column("channel", sa.Text, nullable=False),
        sa.Column("version", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("blob", sa.LargeBinary),
        _tenant_of_thread(),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "channel", "version"),
    )
    op.create_table(
        "checkpoint_writes",
        *_thread_columns(),
        sa.Column("checkpoint_id", sa.Text, nullable=False),
        sa.Column("task_id", sa.Text, nullable=False),
        sa.Column("idx", sa.Integer, nullable=False),
        sa.Column("channel", sa.Text, nullable=False),
        sa.Column("type", sa.Text),
        sa.Column("blob", sa.LargeBinary, nullable=False),
        sa.Column("task_path", sa.Text, nullable=False, server_default=""),
        _tenant_of_thread(),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx"),
    )
    for table in CHECKPOINT_TABLES:
        op.create_index(f"{table}_thread_id_idx", table, ["thread_id"])
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APPLICATION_ROLE}")


def downgrade() -> None:
    for table in reversed(CHECKPOINT_TABLES):
        op.drop_table(table)
