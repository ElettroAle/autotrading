"""An index for the record of what no flow explains on an account, read newest first by keyset on instant and key.

Bug 596, ADR movimenti-non-spiegati-nel-riquadro-del-conto, ADR 0074. A change of the balance within the threshold is
recorded at every reconciliation, so the record of an account grows with its cycles.

Revision ID: 0043
Revises: 0042
"""

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

INDEX = "unattributable_items_of_account_newest"
TABLE = "unattributable_items"
COLUMNS = ("tenant_id", "account_id", "detected_at DESC", "id DESC")


def upgrade() -> None:
    op.create_index(INDEX, TABLE, [sa.text(column) for column in COLUMNS])


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)
