"""Telegram link codes, stored as digests, and the chat linked to each tenant, under row level security.

R1.8.1, ADR 0035.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
DIGEST_OF_TRANSACTION = "decode(NULLIF(current_setting('app.link_code_digest', true), ''), 'hex')"


def upgrade() -> None:
    op.create_table(
        "telegram_link_codes",
        sa.Column("digest", sa.LargeBinary, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "telegram_chats",
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("chat_id", sa.BigInteger, nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for table in ("telegram_link_codes", "telegram_chats"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
    # The bot learns the tenant from the code it receives: a transaction that declares the digest of a code sees
    # that row alone, and only to read it. Knowing the digest means holding the code (ADR 0035).
    op.execute(
        "CREATE POLICY telegram_link_codes_by_digest ON telegram_link_codes FOR SELECT "
        f"USING (digest = {DIGEST_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON telegram_link_codes TO {APPLICATION_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON telegram_chats TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("telegram_chats")
    op.drop_table("telegram_link_codes")
