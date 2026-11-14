import pytest

from autotrading.application.errors import ApplicationError
from autotrading.application.flows.errors import (
    AssetNotTradableError,
    AssetWithOpenPositionError,
    FlowNameInUseError,
    FlowProviderKeyMissingError,
    InvalidFlowSettingError,
)
from autotrading.domain.flows.flow_setting import FlowSetting


@pytest.mark.parametrize(
    ("error", "setting", "status"),
    [
        (FlowNameInUseError(), "name", 409),
        (AssetNotTradableError(("XYZ",)), "assets", 422),
        (AssetWithOpenPositionError(("ETH",)), "assets", 409),
        (InvalidFlowSettingError("fonte non disponibile: x", FlowSetting.SOURCES), "sources", 422),
        (FlowProviderKeyMissingError("openrouter"), "model", 422),
    ],
)
def test_a_refused_setting_names_the_setting_in_its_answer(error: ApplicationError, setting: str, status: int) -> None:
    assert (error.details, error.status_code) == ({"field": setting}, status)
