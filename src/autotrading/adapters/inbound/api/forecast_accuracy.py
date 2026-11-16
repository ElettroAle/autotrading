from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.read_forecast_accuracy import ReadForecastAccuracyCommand
from autotrading.domain.flows.forecast_accuracy import ForecastAccuracy


class ForecastAccuracyResponse(BaseModel):
    """How much the forecasts of one asset and horizon missed in the period (R3.6.1): the mean absolute error as text
    (ADR 0018), the mean percent error on the actual price with two decimals, null without evaluated forecasts.
    """

    asset: str
    horizon_minutes: int
    mean_absolute_error: str | None
    mean_percent_error: str | None
    evaluated: int
    unevaluable: int

    @classmethod
    def of(cls, accuracy: ForecastAccuracy) -> ForecastAccuracyResponse:
        return cls(
            asset=accuracy.asset,
            horizon_minutes=accuracy.horizon_minutes,
            mean_absolute_error=_optional_amount(accuracy.mean_absolute_error),
            mean_percent_error=None if accuracy.mean_percent_error is None else str(accuracy.mean_percent_error),
            evaluated=accuracy.evaluated,
            unevaluable=accuracy.unevaluable,
        )


class FlowForecastAccuracyResponse(BaseModel):
    """The error of the forecasts of a flow in the period, one for every asset and horizon it forecast (ADR
    errore-medio-della-previsione-nell-api).
    """

    forecasts: list[ForecastAccuracyResponse]


def forecast_accuracy_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/forecast-accuracy")
    def read_forecast_accuracy(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        period: Annotated[str, Query(description="all, 7d, 30d o range")] = "all",
        first_day: Annotated[date | None, Query(alias="from", description="primo giorno di un intervallo")] = None,
        last_day: Annotated[date | None, Query(alias="to", description="ultimo giorno di un intervallo")] = None,
    ) -> FlowForecastAccuracyResponse:
        command = ReadForecastAccuracyCommand(flow_id, period, first_day, last_day)
        accuracies = use_cases.read_forecast_accuracy.execute(command)
        return FlowForecastAccuracyResponse(forecasts=[ForecastAccuracyResponse.of(each) for each in accuracies])

    return router


def _optional_amount(amount: Decimal | None) -> str | None:
    return None if amount is None else amount_text(amount)
