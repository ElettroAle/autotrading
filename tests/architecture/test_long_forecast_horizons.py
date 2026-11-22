"""ADR-orizzonti-lunghi-del-forecast: a parameter of a source may admit only a set of choices, each with its label, and
a value outside them is refused with "<parameter>: ammessi <labels>"; the API exposes the choices. The long horizons
have the depth of their daily history as a parameter of the source (365 days by default, from 30 to 1000) and are
forecast on the daily candles. The fixed short horizons and the choice of the long one are replaced by the list of
ADR-parametri-delle-fonti-come-liste-libere.
"""

import ast
from pathlib import Path

import pytest

from autotrading.adapters.inbound.api.sources import SourceParameterResponse
from autotrading.adapters.outbound.forecaster.price_forecast import DECLARATION
from autotrading.domain.sources.errors import SourceParameterNotAmongChoicesError
from autotrading.domain.sources.forecast import FORECAST, LONG_HISTORY_DAYS
from autotrading.domain.sources.source_parameter import ParameterChoice, SourceParameter
from tests.support.architecture import SOURCE_ROOT

USE_CASE = Path(SOURCE_ROOT) / "application" / "sources" / "forecast_asset.py"
DAILY_CANDLES = "daily_history"


def parameter(key: str) -> tuple[object, ...]:
    [found] = [each for each in FORECAST.parameters if each.key == key and isinstance(each, SourceParameter)]
    return found.default, found.minimum, found.maximum, found.choices


def reads_the_daily_candles(source: str) -> bool:
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == DAILY_CANDLES
        for node in ast.walk(ast.parse(source))
    )


def test_adr_orizzonti_lunghi_del_forecast_the_depth_of_the_daily_history_is_a_parameter_of_the_source() -> None:
    assert parameter(LONG_HISTORY_DAYS.key) == (365, 30, 1000, ())
    assert LONG_HISTORY_DAYS.key not in {each.key for each in DECLARATION.parameters}


def test_adr_orizzonti_lunghi_del_forecast_a_value_outside_the_choices_is_refused_listing_their_labels() -> None:
    choices = (ParameterChoice(0, "nessuno"), ParameterChoice(1440, "1 giorno"), ParameterChoice(10080, "1 settimana"))
    horizon = SourceParameter.of_choices("orizzonte", "orizzonte", default=0, choices=choices)

    with pytest.raises(SourceParameterNotAmongChoicesError) as raised:
        horizon.accepted(129600)

    assert str(raised.value) == "orizzonte: ammessi nessuno, 1 giorno, 1 settimana"


def test_adr_orizzonti_lunghi_del_forecast_the_api_exposes_the_choices_of_a_parameter() -> None:
    assert "choices" in SourceParameterResponse.model_fields


@pytest.mark.parametrize(
    ("source", "reading"),
    [
        ("def _long(self):\n    return self._prices.daily_history(asset, days, now)\n", True),
        ("def _long(self):\n    return self._prices.history(asset, days, now)\n", False),
    ],
)
def test_adr_orizzonti_lunghi_del_forecast_a_use_case_that_ignores_the_daily_candles_is_found(
    source: str, reading: bool
) -> None:
    assert reads_the_daily_candles(source) is reading


def test_adr_orizzonti_lunghi_del_forecast_the_long_horizons_are_forecast_on_the_daily_candles() -> None:
    assert reads_the_daily_candles(USE_CASE.read_text(encoding="utf-8"))
