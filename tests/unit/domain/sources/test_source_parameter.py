import pytest

from autotrading.domain.sources.errors import InvalidSourceParameterError
from autotrading.domain.sources.source_parameter import SourceParameter


def news_count() -> SourceParameter:
    return SourceParameter("numero_notizie", "numero notizie", default=10, minimum=1, maximum=50)


@pytest.mark.parametrize("value", [1, 10, 50])
def test_accepts_the_values_within_its_range(value: int) -> None:
    assert news_count().accepts(value)


@pytest.mark.parametrize("value", [0, 51])
def test_refuses_the_values_outside_its_range(value: int) -> None:
    assert not news_count().accepts(value)


@pytest.mark.parametrize(("default", "minimum", "maximum"), [(0, 1, 50), (51, 1, 50), (5, 10, 1)])
def test_a_default_outside_the_range_or_an_empty_range_is_refused(default: int, minimum: int, maximum: int) -> None:
    with pytest.raises(InvalidSourceParameterError) as raised:
        SourceParameter("numero_notizie", "numero notizie", default=default, minimum=minimum, maximum=maximum)

    assert raised.value.key == "numero_notizie"
