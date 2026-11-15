"""The outbox of the external integrations: the messages under row level security, queued by their identity alone.

The queue is the schema of procrastinate 3.11.0, kept in migrations/procrastinate: the schema stays in Alembic and the
library never creates it. Its tables carry no tenant data, only the identity of each message and of its tenant; the
messages, with their recipients and texts, stay in outbox_messages under row level security.
ADR outbox-delle-integrazioni-esterne-con-procrastinate.

Revision ID: 0023
Revises: 0022
"""

from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
QUEUE_SCHEMA = Path(__file__).resolve().parents[1] / "procrastinate" / "schema-3.11.0.sql"
QUEUE_TABLES = ("procrastinate_workers", "procrastinate_jobs", "procrastinate_periodic_defers", "procrastinate_events")
QUEUE_TYPES = ("procrastinate_job_to_defer_v1", "procrastinate_job_event_type", "procrastinate_job_status")
DROP_QUEUE_FUNCTIONS = """
DO $$
DECLARE
    queue_function regprocedure;
BEGIN
    FOR queue_function IN
        SELECT oid::regprocedure FROM pg_proc
         WHERE proname LIKE 'procrastinate%' AND pronamespace = 'public'::regnamespace
    LOOP
        EXECUTE 'DROP FUNCTION ' || queue_function || ' CASCADE';
    END LOOP;
END;
$$
"""


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("integration", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_error", sa.Text),
        sa.CheckConstraint("status IN ('pending', 'delivered', 'failed')", name="outbox_messages_status"),
    )
    op.execute("ALTER TABLE outbox_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE outbox_messages FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY outbox_messages_of_tenant ON outbox_messages "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON outbox_messages TO {APPLICATION_ROLE}")
    # The schema as the library ships it, run as one script: no parameter, so its "%" are no placeholders.
    op.get_bind().connection.driver_connection.execute(QUEUE_SCHEMA.read_text(encoding="utf-8"))
    for table in QUEUE_TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APPLICATION_ROLE}")
        op.execute(f"GRANT USAGE, SELECT ON SEQUENCE {table}_id_seq TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.execute(DROP_QUEUE_FUNCTIONS)
    for table in reversed(QUEUE_TABLES):
        op.execute(f"DROP TABLE {table} CASCADE")
    for queue_type in QUEUE_TYPES:
        op.execute(f"DROP TYPE {queue_type}")
    op.drop_table("outbox_messages")
