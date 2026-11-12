from datetime import UTC, datetime
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.sample_repository import _row_of
from autotrading.domain.sources.source_sample import CycleReference, SourceSample
from autotrading.domain.tenancy.tenant_id import TenantId

PLANNED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
REFERENCE = datetime(2026, 11, 12, 9, 40, tzinfo=UTC)
COLLECTED = datetime(2026, 11, 12, 10, 7, 2, tzinfo=UTC)


def test_a_row_carries_the_cycle_the_source_and_both_instants_of_the_value() -> None:
    tenant_id, flow_id = TenantId.new(), uuid4()
    sample = SourceSample(CycleReference(flow_id, PLANNED), "notizie", None, REFERENCE, COLLECTED, {"titolo": "BTC"})

    assert _row_of(sample, tenant_id) == {
        "tenant_id": tenant_id.value,
        "flow_id": flow_id,
        "cycle_planned_at": PLANNED,
        "source": "notizie",
        "asset": None,
        "reference_at": REFERENCE,
        "collected_at": COLLECTED,
        "sample_values": {"titolo": "BTC"},
    }
