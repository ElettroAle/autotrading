from decimal import Decimal

import pytest

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import (
    CycleIntervalOutOfRangeError,
    ExposureLimitRequiredError,
    FlowNameRequiredError,
    InvalidRiskLimitError,
    MaxLeverageRequiredError,
    ModelRequiredError,
    SourceWeightOutOfRangeError,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, ModelSelection, SourceSelection


def test_a_flow_name_is_kept_without_surrounding_spaces() -> None:
    assert FlowName("  alfa ").value == "alfa"


@pytest.mark.parametrize("name", ["", "   "])
def test_a_flow_name_is_required(name: str) -> None:
    with pytest.raises(FlowNameRequiredError, match=r"^nome del flusso obbligatorio$"):
        FlowName(name)


def test_every_new_flow_id_is_different() -> None:
    assert FlowId.new() != FlowId.new()


@pytest.mark.parametrize("minutes", [1, 15, 1440])
def test_the_cycle_interval_goes_from_one_minute_to_one_day(minutes: int) -> None:
    assert CycleInterval(minutes).minutes == minutes


@pytest.mark.parametrize("minutes", [0, -5, 1441])
def test_a_cycle_interval_out_of_range_is_refused(minutes: int) -> None:
    with pytest.raises(CycleIntervalOutOfRangeError, match=r"^intervallo di ciclo fuori da 1-1440 minuti$"):
        CycleInterval(minutes)


def test_the_cycle_interval_is_fifteen_minutes_when_not_given() -> None:
    assert CycleInterval.of(None) == CycleInterval(15)
    assert CycleInterval.of(30) == CycleInterval(30)


@pytest.mark.parametrize(
    ("status", "not_stopped"),
    [
        (FlowStatus.STOPPED, False),
        (FlowStatus.ACTIVE, True),
        (FlowStatus.PAUSED, True),
        (FlowStatus.ARCHIVED, False),
    ],
)
def test_only_active_and_paused_flows_are_not_stopped(status: FlowStatus, *, not_stopped: bool) -> None:
    assert status.not_stopped is not_stopped


def test_the_statuses_read_as_the_user_reads_them() -> None:
    assert [status.value for status in FlowStatus] == ["fermo", "attivo", "in pausa", "archiviato"]


def test_risk_limits_need_the_leverage_and_one_exposure() -> None:
    margin_only = RiskLimits(5, Decimal(10))
    value_only = RiskLimits(1, None, Decimal(100))

    assert (margin_only.max_margin_exposure_percent, margin_only.max_value_exposure_percent) == (Decimal(10), None)
    assert (value_only.max_leverage, value_only.max_value_exposure_percent) == (1, Decimal(100))


def test_the_maximum_leverage_is_required_before_anything_else() -> None:
    with pytest.raises(MaxLeverageRequiredError, match=r"^la leva massima è obbligatoria$"):
        RiskLimits(None)


def test_at_least_one_exposure_is_required() -> None:
    with pytest.raises(ExposureLimitRequiredError, match=r"^almeno un limite di esposizione è obbligatorio$"):
        RiskLimits(0)


def test_a_leverage_below_one_is_refused() -> None:
    with pytest.raises(InvalidRiskLimitError, match=r"^limite di rischio non valido: leva massima$"):
        RiskLimits(0, Decimal(10))


@pytest.mark.parametrize("percent", [Decimal(0), Decimal(-1), Decimal("100.01"), Decimal("NaN"), Decimal("Infinity")])
def test_an_exposure_outside_zero_to_hundred_percent_is_refused(percent: Decimal) -> None:
    with pytest.raises(InvalidRiskLimitError, match=r"^limite di rischio non valido: esposizione massima del margine$"):
        RiskLimits(5, percent)
    with pytest.raises(InvalidRiskLimitError, match=r"^limite di rischio non valido: esposizione massima del valore$"):
        RiskLimits(5, Decimal(10), percent)


def test_a_model_selection_needs_a_model() -> None:
    with pytest.raises(ModelRequiredError, match=r"^modello obbligatorio$"):
        ModelSelection(" ")


def test_a_source_weighs_five_unless_chosen() -> None:
    assert SourceSelection("notizie").weight == DEFAULT_WEIGHT == 5


@pytest.mark.parametrize("weight", [1, 10])
def test_a_source_weighs_from_one_to_ten(weight: int) -> None:
    assert SourceSelection("notizie", weight).weight == weight


@pytest.mark.parametrize("weight", [0, 11])
def test_a_weight_out_of_range_is_refused(weight: int) -> None:
    with pytest.raises(SourceWeightOutOfRangeError, match=r"^peso fuori da 1-10: notizie$"):
        SourceSelection("notizie", weight)
