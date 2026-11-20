from decimal import Decimal

from autotrading.domain.sources.volume_aggregate import AGGREGATE, volume_aggregate
from autotrading.domain.sources.volume_figures import VolumeFigures, volume_weighted

LARGE = VolumeFigures(Decimal(300), Decimal(2), Decimal("0.6"))
SMALL = VolumeFigures(Decimal(100), Decimal(1), Decimal("0.2"))


def test_two_adapters_that_measured_the_asset_have_an_aggregate_weighted_on_their_volumes() -> None:
    assert volume_aggregate((LARGE, SMALL)) == volume_weighted((LARGE, SMALL))


def test_a_single_adapter_has_no_aggregate() -> None:
    assert volume_aggregate((LARGE,)) is None
    assert volume_aggregate(()) is None


def test_the_context_names_the_aggregate_as_its_adapter() -> None:
    assert AGGREGATE == "aggregato"
