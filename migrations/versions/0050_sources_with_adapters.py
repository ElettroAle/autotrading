"""The sources of every flow in the model with adapters, in a new version of its configuration.

Every flow whose last version has the sources before the adapters gets a version after it, with each source passed to
its adapter, weights and parameters unchanged; the versions before stay as they are. Every value collected gets the
adapter that read it, and the sentiment values the source they now belong to. R4.1.1, ADR
migrazione-delle-fonti-al-modello-ad-adapter.

Revision ID: 0050
Revises: 0049
"""

from collections.abc import Callable

import sqlalchemy as sa
from alembic import op

from autotrading.adapters.outbound.sqlalchemy.source_correspondence import (
    MIGRATION_MARKER,
    SOURCE_AND_ADAPTER,
    migrated_document,
)

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None

_flow_versions = sa.table(
    "flow_versions",
    sa.column("flow_id", sa.Uuid),
    sa.column("version", sa.Integer),
    sa.column("tenant_id", sa.Uuid),
    sa.column("configuration", sa.JSON),
)
_source_samples = sa.table(
    "source_samples",
    sa.column("source", sa.Text),
    sa.column("adapter", sa.Text),
)


def upgrade() -> None:
    _without_row_security("flow_versions", _versions_in_adapters)
    op.add_column("source_samples", sa.Column("adapter", sa.Text, nullable=True))
    _without_row_security("source_samples", _samples_with_adapter)
    op.alter_column("source_samples", "adapter", nullable=False)


def downgrade() -> None:
    marker, origin = MIGRATION_MARKER
    _without_row_security(
        "flow_versions",
        lambda: op.execute(
            sa.text("DELETE FROM flow_versions WHERE configuration::jsonb ->> :marker = :origin").bindparams(
                marker=marker, origin=origin
            )
        ),
    )
    _without_row_security("source_samples", _samples_before_the_adapters)
    op.drop_column("source_samples", "adapter")


def _versions_in_adapters() -> None:
    latest = op.get_bind().execute(
        sa.text(
            "SELECT DISTINCT ON (flow_id) flow_id, tenant_id, version, configuration FROM flow_versions"
            " ORDER BY flow_id, version DESC"
        ).columns(sa.column("configuration", sa.JSON))
    )
    rows = [
        {"flow_id": flow_id, "version": version + 1, "tenant_id": tenant_id, "configuration": document}
        for flow_id, tenant_id, version, configuration in latest
        if (document := migrated_document(configuration)) is not None
    ]
    if rows:
        op.bulk_insert(_flow_versions, rows)


def _samples_with_adapter() -> None:
    for old, (source, adapter) in SOURCE_AND_ADAPTER.items():
        op.execute(
            _source_samples.update().where(_source_samples.c.source == old).values(source=source, adapter=adapter)
        )
    # A value of a source the platform no longer has keeps its name as the adapter, as the reading of the flows does.
    op.execute(
        _source_samples.update().where(_source_samples.c.adapter.is_(None)).values(adapter=_source_samples.c.source)
    )


def _samples_before_the_adapters() -> None:
    for old, (source, adapter) in SOURCE_AND_ADAPTER.items():
        op.execute(
            _source_samples.update()
            .where((_source_samples.c.source == source) & (_source_samples.c.adapter == adapter))
            .values(source=old)
        )


def _without_row_security(table: str, change: Callable[[], None]) -> None:
    # Row level security forced on the table hides every row from the owner too, without a tenant: the rows of every
    # tenant change only while it is lifted, inside the transaction of the migration.
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    change()
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
