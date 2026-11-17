import { fakeClock } from './clock';
import { contains, windowOf } from './flow-statistics';
import type { FakeForecast } from './platform';

const sum = (values: number[]): number => values.reduce((total, value) => total + value, 0);

const keyOf = (forecast: FakeForecast): string => `${forecast.asset}|${forecast.horizonMinutes}`;

const byAssetThenHorizon = (first: FakeForecast, second: FakeForecast): number =>
  first.asset.localeCompare(second.asset) || first.horizonMinutes - second.horizonMinutes;

/**
 * The error of the forecasts of a flow as the API measures and writes it (R3.6.1): one entry for every asset and
 * horizon with an expired forecast, the forecasts counted in the period their horizon expires in, the mean absolute
 * error as text and the mean percent error on the actual price with two decimals, null without evaluated forecasts.
 */
export const forecastAccuracyOf = (
  forecasts: FakeForecast[],
  search: URLSearchParams,
  now = fakeClock.now(),
) => {
  const window = windowOf(search, now);
  const expired = forecasts
    .filter((forecast) => forecast.expiresAt.getTime() <= now)
    .sort(byAssetThenHorizon);
  const pairs = [...new Map(expired.map((forecast) => [keyOf(forecast), forecast])).values()];
  return {
    forecasts: pairs.map(({ asset, horizonMinutes }) => {
      const inPeriod = expired.filter(
        (forecast) =>
          keyOf(forecast) === `${asset}|${horizonMinutes}` && contains(window, forecast.expiresAt),
      );
      const errors = inPeriod.flatMap(({ predictedPrice, actualPrice }) =>
        actualPrice === null
          ? []
          : [{ absolute: Math.abs(predictedPrice - actualPrice), actual: actualPrice }],
      );
      const none = errors.length === 0;
      const absolute = sum(errors.map((error) => error.absolute)) / errors.length;
      const percent =
        sum(errors.map((error) => (error.absolute / error.actual) * 100)) / errors.length;
      return {
        asset,
        horizon_minutes: horizonMinutes,
        mean_absolute_error: none ? null : String(absolute),
        mean_percent_error: none ? null : percent.toFixed(2),
        evaluated: errors.length,
        unevaluable: inPeriod.length - errors.length,
      };
    }),
  };
};
