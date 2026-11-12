from datetime import UTC, datetime
from uuid import uuid4

import pytest

from autotrading.domain.sources.errors import InvalidSourceSampleError
from autotrading.domain.sources.source_sample import CycleReference, SourceSample, SourceValue

PLANNED = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
REFERENCE = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
COLLECTED = datetime(2026, 11, 12, 10, 0, 3, tzinfo=UTC)
CYCLE = CycleReference(uuid4(), PLANNED)


def test_a_sample_keeps_the_value_with_its_reference_and_its_collection() -> None:
    values = {"prezzo": "100"}

    sample = SourceSample.of(CYCLE, "indicatori", "BTC", SourceValue(REFERENCE, values), COLLECTED)

    assert sample == SourceSample(CYCLE, "indicatori", "BTC", REFERENCE, COLLECTED, {"prezzo": "100"})


def test_a_sample_owns_a_copy_of_the_values() -> None:
    values = {"prezzo": "100"}

    sample = SourceSample.of(CYCLE, "indicatori", "BTC", SourceValue(REFERENCE, values), COLLECTED)
    values["prezzo"] = "200"

    assert sample.values == {"prezzo": "100"}


@pytest.mark.parametrize(
    ("planned", "reference", "collected"),
    [
        (PLANNED.replace(tzinfo=None), REFERENCE, COLLECTED),
        (PLANNED, REFERENCE.replace(tzinfo=None), COLLECTED),
        (PLANNED, REFERENCE, COLLECTED.replace(tzinfo=None)),
    ],
)
def test_an_instant_without_time_zone_is_a_defect(planned: datetime, reference: datetime, collected: datetime) -> None:
    with pytest.raises(InvalidSourceSampleError, match="valore raccolto non valido") as raised:
        SourceSample(CycleReference(CYCLE.flow_id, planned), "notizie", None, reference, collected, {})

    assert raised.value.status_code == 500
