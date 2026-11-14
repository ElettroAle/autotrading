import pytest

from autotrading.domain.errors import DomainError
from autotrading.domain.flows.errors import (
    AccountNotChangeableError,
    AllocatedCapitalNotPositiveError,
    AssetsAssignedToOtherFlowError,
    AssetsRequiredError,
    CapitalAboveAvailableCapitalError,
    CapitalAboveFreeCapitalError,
    CapitalBelowFlowMinimumError,
    CycleIntervalOutOfRangeError,
    ExposureLimitRequiredError,
    FlowNameRequiredError,
    InvalidRiskLimitError,
    MaxLeverageRequiredError,
    ModelRequiredError,
    RepeatedSourceError,
    SourceWeightOutOfRangeError,
)
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.risk_limits import LEVERAGE, VALUE_EXPOSURE


@pytest.mark.parametrize(
    ("error", "setting"),
    [
        (FlowNameRequiredError(), "name"),
        (ModelRequiredError(), "model"),
        (CycleIntervalOutOfRangeError(), "cycle_minutes"),
        (AssetsRequiredError(), "assets"),
        (MaxLeverageRequiredError(), "max_leverage"),
        (ExposureLimitRequiredError(), "max_margin_exposure_percent"),
        (InvalidRiskLimitError(VALUE_EXPOSURE, FlowSetting.MAX_VALUE_EXPOSURE), "max_value_exposure_percent"),
        (SourceWeightOutOfRangeError("notizie"), "sources"),
        (RepeatedSourceError("notizie"), "sources"),
        (AllocatedCapitalNotPositiveError(), "allocated_capital"),
        (CapitalAboveFreeCapitalError("500 USDC"), "allocated_capital"),
        (CapitalAboveAvailableCapitalError("500 USDC"), "allocated_capital"),
        (CapitalBelowFlowMinimumError("10 USDC"), "allocated_capital"),
        (AccountNotChangeableError(), "account_id"),
        (AssetsAssignedToOtherFlowError("beta", ("ETH",)), "assets"),
    ],
)
def test_a_refused_setting_names_the_setting_in_its_answer(error: DomainError, setting: str) -> None:
    assert error.details == {"field": setting}


def test_an_invalid_risk_limit_tells_the_limit_by_its_label() -> None:
    assert (
        str(InvalidRiskLimitError(LEVERAGE, FlowSetting.MAX_LEVERAGE)) == "limite di rischio non valido: leva massima"
    )


def test_a_conflict_on_the_assets_keeps_its_status() -> None:
    assert AssetsAssignedToOtherFlowError("beta", ("ETH",)).status_code == 409
