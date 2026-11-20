from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import TypedDict, cast

import httpx

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceHistory
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration

# The first fit of an asset takes seconds on one vCPU; the wait of the cycle bounds the source anyway.
TIMEOUT_SECONDS = 60.0
# The adapter of the forecast (R4.1.1): it forecasts from any history it is sent, a past one too.
DECLARATION = SourceAdapterDeclaration(
    "Prophet",
    "Previsione di Prophet dal servizio forecaster dell'installazione, sullo storico dei prezzi dell'exchange.",
    (),
    (),
    offers_history=True,
)


class _HorizonForecast(TypedDict):
    horizon_minutes: int
    predicted_price: str


class _ForecastDocument(TypedDict):
    forecasts: list[_HorizonForecast]


class ForecasterPriceForecastAdapter:
    """The forecasts of Prophet from the forecaster service of the installation (R1.3.5, ADR 0107)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def declaration(self) -> SourceAdapterDeclaration:
        return DECLARATION

    def predict(
        self, asset: str, history: PriceHistory, horizons: tuple[ForecastHorizon, ...]
    ) -> Mapping[ForecastHorizon, Decimal]:
        document = cast("_ForecastDocument", self._document(_request_of(asset, history, horizons)))
        try:
            predicted = {entry["horizon_minutes"]: Decimal(entry["predicted_price"]) for entry in document["forecasts"]}
            return {horizon: predicted[horizon.minutes] for horizon in horizons}
        except (KeyError, TypeError, InvalidOperation) as error:
            raise SourceUnavailableError(FORECAST.name) from error

    def _document(self, request: dict[str, object]) -> object:
        try:
            response = self._client.post("/forecast", json=request, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            # Any other shape fails on the first lookup, in predict.
            document: object = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise SourceUnavailableError(FORECAST.name) from error
        return document


def _request_of(asset: str, history: PriceHistory, horizons: tuple[ForecastHorizon, ...]) -> dict[str, object]:
    return {
        "asset": asset,
        "history_days": history.requested_days,
        "points": [{"at": point.at.isoformat(), "price": str(point.price)} for point in history.points],
        **_horizons_of(horizons),
    }


def _horizons_of(horizons: tuple[ForecastHorizon, ...]) -> dict[str, list[int]]:
    """The long horizons go in days with their daily history, the short ones in minutes (ADR
    orizzonti-lunghi-del-forecast): the service keeps a model apart for each kind of candles.
    """
    if all(horizon.on_daily_candles for horizon in horizons):
        return {"horizons_days": [horizon.days for horizon in horizons]}
    return {"horizons_minutes": [horizon.minutes for horizon in horizons]}
