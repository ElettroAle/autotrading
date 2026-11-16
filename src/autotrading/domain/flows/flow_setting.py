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
    MAX_TOTAL_MARGIN_EXPOSURE = "max_total_margin_exposure_percent"
    MAX_TOTAL_VALUE_EXPOSURE = "max_total_value_exposure_percent"
    ALLOCATED_CAPITAL = "allocated_capital"
    SYSTEM_PROMPT = "system_prompt"
    MAX_CONSECUTIVE_FAILURES = "max_consecutive_failures"
    MAX_DAILY_LOSS = "max_daily_loss_percent"
    MAX_DRAWDOWN = "max_drawdown_percent"
    OPENINGS_RESUME = "openings_resume"
    DEFAULT_STOP_LOSS = "default_stop_loss_percent"
    DEFAULT_TAKE_PROFIT = "default_take_profit_percent"
