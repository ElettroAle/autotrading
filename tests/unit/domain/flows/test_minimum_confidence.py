import pytest

from autotrading.domain.flows.errors import InvalidMinimumConfidenceError
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.minimum_confidence import MinimumConfidence


@pytest.mark.parametrize("value", [0, 60, 100])
def test_accepts_a_minimum_confidence_from_0_to_100(value: int) -> None:
    assert MinimumConfidence(value).value == value


@pytest.mark.parametrize("value", [-1, 101])
def test_refuses_a_minimum_confidence_out_of_range_naming_the_setting(value: int) -> None:
    with pytest.raises(InvalidMinimumConfidenceError, match=r"^la confidenza minima va da 0 a 100$") as refused:
        MinimumConfidence(value)

    assert refused.value.setting is FlowSetting.MINIMUM_CONFIDENCE
    assert refused.value.details == {"field": "minimum_confidence"}
    assert refused.value.status_code == 422


@pytest.mark.parametrize(("confidence", "admitted"), [(59, False), (60, True), (61, True)])
def test_admits_a_confidence_equal_to_the_minimum_or_above(confidence: int, *, admitted: bool) -> None:
    assert MinimumConfidence(60).admits(confidence) is admitted


def test_reads_as_its_number() -> None:
    assert str(MinimumConfidence(60)) == "60"


def test_an_optional_minimum_confidence_is_absent_when_not_given() -> None:
    assert MinimumConfidence.optional(None) is None
    assert MinimumConfidence.optional(45) == MinimumConfidence(45)
