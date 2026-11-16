"""R3.6.1: the mean error of the forecasts of a flow, read on the use cases of the flows context (ADR
errore-medio-della-previsione-nell-api). playwright-bdd runs the scenario of the flow page on the dashboard (ADR
errore-della-previsione-nella-pagina-del-flusso).
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.read_forecast_accuracy import ReadForecastAccuracyCommand
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.forecast_accuracy import ForecastAccuracy
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from tests.support.flows import a_configuration, a_flow
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.6-qualita-delle-previsioni/R3.6.1-errore-medio-della-previsione.feature")

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
HORIZONS = {"1 ora": ForecastHorizon.HOUR_1, "15 minuti": ForecastHorizon.MINUTES_15}
ACTUAL = Decimal(60000)
FORECAST_SOURCE = SourceSelection("forecast", parameters={"profondita_storico_giorni": 7})


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def day(text: str) -> date:
    return datetime.strptime(text, "%d/%m/%Y").replace(tzinfo=UTC).date()


@dataclass
class ForecastErrors:
    platform: Platform = field(default_factory=Platform)
    flows: dict[str, Flow] = field(default_factory=dict)
    asset: str = ""
    recorded: int = 0
    seen: tuple[ForecastAccuracy, ...] | None = None
    consulted: tuple[str, int] | None = None

    def __post_init__(self) -> None:
        self.platform.now = NOW

    def give_flow(self, user: str, name: str, asset: str) -> None:
        configuration = replace(a_configuration(assets=(asset,)), sources=(FORECAST_SOURCE,))
        flow = a_flow(self.platform.tenant_of(user), name=name, configuration=configuration)
        self.platform.flows.flows.append(flow)
        self.asset, self.flows[name] = asset, flow

    def forecast(
        self,
        flow: str,
        predicted: Decimal,
        actual: Decimal | None,
        horizon: ForecastHorizon = ForecastHorizon.HOUR_1,
        expires_at: datetime | None = None,
    ) -> None:
        """A forecast the flow recorded: unless told, it expired an hour ago, each a minute before the previous."""
        self.recorded += 1
        expiry = NOW - timedelta(hours=1, minutes=self.recorded) if expires_at is None else expires_at
        owner = self.flows[flow]
        made_at = expiry - horizon.length
        recorded = PriceForecast(owner.id.value, self.asset, horizon, made_at, ACTUAL, predicted, 7, False, actual)
        self.platform.forecasts_of(owner.tenant_id).add(recorded)

    def forecast_with_error(
        self,
        flow: str,
        error: Decimal,
        horizon: ForecastHorizon = ForecastHorizon.HOUR_1,
        expires_at: datetime | None = None,
    ) -> None:
        self.forecast(flow, ACTUAL + error, ACTUAL, horizon, expires_at)

    def consult(self, user: str, flow: str, asset: str, horizon: str, days: tuple[date, date] | None = None) -> None:
        command = ReadForecastAccuracyCommand(self.flows[flow].id.value)
        if days is not None:
            command = ReadForecastAccuracyCommand(self.flows[flow].id.value, "range", *days)
        self.seen = self.platform.use_cases_of(user).read_forecast_accuracy.execute(command)
        self.consulted = (asset, HORIZONS[horizon].minutes)

    def accuracy(self) -> ForecastAccuracy | None:
        """The error of the asset and horizon consulted; none when the flow has no forecast of them."""
        assert self.seen is not None, "nessun errore della previsione consultato"
        found = [entry for entry in self.seen if (entry.asset, entry.horizon_minutes) == self.consulted]
        return found[0] if found else None

    def shown(self) -> ForecastAccuracy:
        accuracy = self.accuracy()
        assert accuracy is not None, f"nessun errore per {self.consulted}: {self.seen}"
        return accuracy


@pytest.fixture
def errors() -> ForecastErrors:
    return ForecastErrors()


@given(quoted('che "{user}" ha il flusso "{flow}" con la fonte forecast su "{asset}" a 1 ora'))
def flow_with_forecast(errors: ForecastErrors, user: str, flow: str, asset: str) -> None:
    errors.give_flow(user, flow, asset)


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha previsto (?P<predicted>\d+) per un istante in cui il prezzo effettivo è stato '
        r"(?P<actual>\d+)$"
    )
)
def forecast_and_actual(errors: ForecastErrors, flow: str, predicted: str, actual: str) -> None:
    errors.forecast(flow, amount(predicted), amount(actual))


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una previsione scaduta con errore assoluto (?P<error>\d+) e una previsione per un '
        r"istante futuro$"
    )
)
def expired_and_future(errors: ForecastErrors, flow: str, error: str) -> None:
    errors.forecast_with_error(flow, amount(error))
    errors.forecast(flow, ACTUAL, None, expires_at=NOW + timedelta(minutes=30))


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha anche previsioni su "[^"]+" a (?P<horizon>.+) con errore medio assoluto '
        r"(?P<error>\d+)$"
    )
)
def forecasts_of_another_horizon(errors: ForecastErrors, flow: str, horizon: str, error: str) -> None:
    mean = amount(error)
    errors.forecast_with_error(flow, mean - 100, HORIZONS[horizon])
    errors.forecast_with_error(flow, -(mean + 100), HORIZONS[horizon])


@given(
    parsers.re(
        r'^che le previsioni di "(?P<flow>[^"]+)" su "[^"]+" a (?P<horizon>.+) hanno errore medio assoluto '
        r"(?P<error>\d+)$"
    )
)
def forecasts_with_mean_error(errors: ForecastErrors, flow: str, horizon: str, error: str) -> None:
    mean = amount(error)
    errors.forecast_with_error(flow, mean + 50, HORIZONS[horizon])
    errors.forecast_with_error(flow, -(mean - 50), HORIZONS[horizon])


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una previsione scaduta con errore assoluto (?P<error>\d+) e una previsione scaduta '
        r"senza prezzo effettivo$"
    )
)
def expired_without_actual(errors: ForecastErrors, flow: str, error: str) -> None:
    errors.forecast_with_error(flow, amount(error))
    errors.forecast(flow, ACTUAL, None)


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una previsione del (?P<first>[\d/]+) con errore assoluto (?P<first_error>\d+) '
        r"e una del (?P<second>[\d/]+) con errore assoluto (?P<second_error>\d+)$"
    )
)
def forecasts_of_two_days(
    errors: ForecastErrors, *, flow: str, first: str, first_error: str, second: str, second_error: str
) -> None:
    for text, error in ((first, first_error), (second, second_error)):
        expiry = datetime.combine(day(text), datetime.min.time(), tzinfo=UTC) + timedelta(hours=11)
        errors.forecast_with_error(flow, amount(error), expires_at=expiry)


@given(quoted('che "{flow}" non ha previsioni scadute nel periodo'))
def no_expired_forecast(errors: ForecastErrors, flow: str) -> None:
    errors.forecast(flow, ACTUAL, None, expires_at=NOW + timedelta(minutes=30))


@given(
    parsers.re(
        r'^che le previsioni di "(?P<flow>[^"]+)" su "[^"]+" a 1 ora hanno errore medio assoluto \d+ e percentuale '
        r"[\d,]+% su 2 previsioni$"
    )
)
def forecasts_of_the_page(errors: ForecastErrors, flow: str) -> None:
    errors.forecast(flow, Decimal(60500), Decimal(60000))
    errors.forecast(flow, Decimal(61000), Decimal(61400))


@when(quoted('"{user}" consulta l\'errore della previsione di "{flow}" su "{asset}" a {horizon} dal {first} al {last}'))
def consult_period(
    errors: ForecastErrors, *, user: str, flow: str, asset: str, horizon: str, first: str, last: str
) -> None:
    errors.consult(user, flow, asset, horizon, (day(first), day(last)))


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" consulta l\'errore della previsione di "(?P<flow>[^"]+)" su "(?P<asset>[^"]+)" a '
        r"(?P<horizon>1 ora|15 minuti)$"
    )
)
def consult(errors: ForecastErrors, user: str, flow: str, asset: str, horizon: str) -> None:
    errors.consult(user, flow, asset, horizon)


@when(quoted('"{user}" apre la pagina del flusso "{flow}" nella dashboard'))
def open_flow_page(errors: ForecastErrors, user: str, flow: str) -> None:
    # The page reads the error over its period, the whole life unless the user chooses another.
    errors.consult(user, flow, errors.asset, "1 ora")


@then(parsers.re(r"^l'errore medio assoluto è (?P<error>\d+)$"))
def mean_absolute_error(errors: ForecastErrors, error: str) -> None:
    assert errors.shown().mean_absolute_error == amount(error)


@then(parsers.re(r"^l'errore medio percentuale è (?P<percent>[\d,]+)%$"))
def mean_percent_error(errors: ForecastErrors, percent: str) -> None:
    assert errors.shown().mean_percent_error == amount(percent)


@then(parsers.re(r"^le previsioni valutate sono (?P<count>\d+)$"))
def evaluated(errors: ForecastErrors, count: str) -> None:
    assert errors.shown().evaluated == int(count)


@then(parsers.re(r"^le previsioni non valutabili sono (?P<count>\d+)$"))
def unevaluable(errors: ForecastErrors, count: str) -> None:
    assert errors.shown().unevaluable == int(count)


@then(quoted('l\'errore è "non disponibile nel periodo"'))
def not_available(errors: ForecastErrors) -> None:
    accuracy = errors.accuracy()
    # Nothing to measure: either no forecast expired in the period, or the flow has none of the asset and horizon.
    assert accuracy is None or (accuracy.evaluated, accuracy.mean_absolute_error) == (0, None)
    assert errors.seen is not None
    assert all(entry.evaluated == 0 for entry in errors.seen)


@then(
    parsers.re(
        r'^la pagina mostra per "(?P<asset>[^"]+)" a 1 ora errore medio (?P<error>\d+), (?P<percent>[\d,]+)%, '
        r"(?P<count>\d+) previsioni valutate$"
    )
)
def page_shows(errors: ForecastErrors, asset: str, error: str, percent: str, count: str) -> None:
    shown = errors.shown()
    assert shown.asset == asset
    assert (shown.mean_absolute_error, shown.mean_percent_error) == (amount(error), amount(percent))
    assert shown.evaluated == int(count)
