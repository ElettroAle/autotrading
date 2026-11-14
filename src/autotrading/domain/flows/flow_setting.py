from enum import StrEnum


class FlowSetting(StrEnum):
    """A setting of a flow, by the name the user gives it a value with: a refusal names the one it concerns (R2.3.3)."""

    NAME = "name"
    ACCOUNT = "account_id"
    ASSETS = "assets"
    CYCLE_MINUTES = "cycle_minutes"
    MODEL = "model"
    MODEL_PARAMETERS = "model_parameters"
    SOURCES = "sources"
    MAX_LEVERAGE = "max_leverage"
    MAX_MARGIN_EXPOSURE = "max_margin_exposure_percent"
    MAX_VALUE_EXPOSURE = "max_value_exposure_percent"
    ALLOCATED_CAPITAL = "allocated_capital"
