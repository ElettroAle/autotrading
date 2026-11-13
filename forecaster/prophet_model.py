"""The only module that speaks Prophet: training on a price history and forecasting one instant."""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pandas
from prophet import Prophet
from prophet.serialize import model_from_json, model_to_json
from prophet.utilities import warm_start_params

# The interval needs samples; a hundred keep the forecast well under a second.
UNCERTAINTY_SAMPLES = 100

# cmdstanpy reports every chain it starts at INFO: one line per fit says nothing an operator needs.
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


@dataclass(frozen=True, slots=True)
class PricePoint:
    at: datetime
    price: Decimal


@dataclass(frozen=True, slots=True)
class TrainedModel:
    """A fitted model, serialized in JSON as Prophet recommends instead of pickle, with the last instant it saw."""

    json: str
    trained_until: datetime


@dataclass(frozen=True, slots=True)
class Forecast:
    predicted: Decimal
    lower: Decimal
    upper: Decimal


def fit(points: list[PricePoint], warm_start: TrainedModel | None) -> TrainedModel:
    """A model of the history; the parameters of a previous model of the same series make the fit faster."""
    frame = pandas.DataFrame(
        {"ds": [_naive(point.at) for point in points], "y": [float(point.price) for point in points]}
    )
    model = Prophet(uncertainty_samples=UNCERTAINTY_SAMPLES)
    if warm_start is None:
        model.fit(frame)
    else:
        model.fit(frame, init=warm_start_params(model_from_json(warm_start.json)))
    return TrainedModel(model_to_json(model), points[-1].at)


def predict(model: TrainedModel, at: datetime) -> Forecast:
    row = model_from_json(model.json).predict(pandas.DataFrame({"ds": [_naive(at)]})).iloc[0]
    return Forecast(_decimal(row["yhat"]), _decimal(row["yhat_lower"]), _decimal(row["yhat_upper"]))


def _naive(at: datetime) -> datetime:
    # Prophet refuses instants with a time zone; every instant of the service is UTC.
    return at.replace(tzinfo=None)


def _decimal(value: object) -> Decimal:
    return Decimal(repr(float(str(value))))
