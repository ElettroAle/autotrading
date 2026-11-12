from collections.abc import Sequence

from sqlalchemy import Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.tables import source_samples
from autotrading.domain.sources.source_sample import SourceSample
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemySampleRepositoryAdapter:
    """Bound to the tenant of the flow: every transaction declares it, and row level security does the rest (R1.3.8)."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, samples: Sequence[SourceSample]) -> None:
        if not samples:
            return
        rows = [_row_of(sample, self._tenant_id) for sample in samples]
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous cycle.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            connection.execute(insert(source_samples), rows)


def _row_of(sample: SourceSample, tenant_id: TenantId) -> dict[str, object]:
    return {
        "tenant_id": tenant_id.value,
        "flow_id": sample.cycle.flow_id,
        "cycle_planned_at": sample.cycle.planned_at,
        "source": sample.source,
        "asset": sample.asset,
        "reference_at": sample.reference_at,
        "collected_at": sample.collected_at,
        "sample_values": dict(sample.values),
    }
