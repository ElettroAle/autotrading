"""The bot learns the tenants of a linked chat from the chat itself, for the test notification.

R1.8.1, ADR 0081.

Revision ID: 0018
Revises: 0017
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

CHAT_OF_TRANSACTION = "NULLIF(current_setting('app.telegram_chat_id', true), '')::bigint"


def upgrade() -> None:
    # A transaction that declares a chat sees the links of that chat alone, and only to read them: only Telegram
    # delivers a message from a chat, so declaring it means being that chat (ADR 0081).
    op.execute(
        f"CREATE POLICY telegram_chats_by_chat ON telegram_chats FOR SELECT USING (chat_id = {CHAT_OF_TRANSACTION})"
    )


def downgrade() -> None:
    op.execute("DROP POLICY telegram_chats_by_chat ON telegram_chats")
