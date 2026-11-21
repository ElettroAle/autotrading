from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import TimeframeNotAvailableError
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.long_trend import (
    DAILY_CANDLES,
    DAILY_TIMEFRAME,
    LONG_TREND,
    LongTrendChoice,
    daily_timeframe_of,
    long_trend,
)
from autotrading.domain.sources.timeframe import Timeframe

# The close of the last daily candle: midnight UTC, the end of the day before.
LAST_CLOSE = datetime(2026, 11, 21, tzinfo=UTC)


def daily(closes: list[Decimal]) -> list[Candle]:
    last = len(closes) - 1
    return [
        Candle(LAST_CLOSE - timedelta(days=last - index), close, Decimal(1), close + 1, close - 1)
        for index, close in enumerate(closes)
    ]


def rising(count: int) -> list[Decimal]:
    return [Decimal(100 + index) for index in range(count)]


# The parameter


def test_the_long_trend_is_a_parameter_off_by_default() -> None:
    assert (LONG_TREND.key, LONG_TREND.label, LONG_TREND.default, LONG_TREND.minimum, LONG_TREND.maximum) == (
        "tendenza_lunga",
        "tendenza lunga",
        0,
        0,
        1,
    )
    assert LONG_TREND in INDICATORS.parameters


def test_a_choice_follows_the_setting_and_the_default() -> None:
    assert LongTrendChoice.of({"tendenza_lunga": 1}).active
    assert not LongTrendChoice.of({"tendenza_lunga": 0}).active
    assert not LongTrendChoice.of({}).active


def test_the_trend_reads_sixty_one_daily_candles() -> None:
    assert DAILY_CANDLES == 61
    assert Timeframe(24 * 60) == DAILY_TIMEFRAME


def test_the_daily_timeframe_is_one_the_market_publishes() -> None:
    assert daily_timeframe_of((Timeframe(240), Timeframe(1440))) == Timeframe(1440)


def test_a_market_without_daily_candles_has_no_long_trend() -> None:
    with pytest.raises(TimeframeNotAvailableError) as raised:
        daily_timeframe_of((Timeframe(240), Timeframe(10080)))

    assert raised.value.cycle_minutes == 1440


# The values


def test_the_change_of_each_horizon_compares_the_last_close_with_the_one_n_days_before() -> None:
    closes = [Decimal(52000)] * 61
    closes[-31], closes[-1] = Decimal(50000), Decimal(55000)

    values = long_trend(daily(closes))

    assert values["tendenza.variazione_30g"] == Decimal(10)
    assert values["tendenza.variazione_7g"] == (Decimal(55000) / Decimal(52000) - 1) * 100
    assert values["tendenza.variazione_60g"] == (Decimal(55000) / Decimal(52000) - 1) * 100


def test_every_horizon_has_its_own_change() -> None:
    closes = rising(61)

    values = long_trend(daily(closes))

    assert {days: values[f"tendenza.variazione_{days}g"] for days in (7, 14, 30, 60)} == {
        days: (closes[-1] / closes[-1 - days] - 1) * 100 for days in (7, 14, 30, 60)
    }


def test_the_channel_spans_the_closes_of_the_twenty_days_before_the_last() -> None:
    closes = rising(61)
    closes[-1] = Decimal(1000)
    closes[-22] = Decimal(1)

    values = long_trend(daily(closes))

    assert values["tendenza.massimo_20g"] == closes[-2]
    assert values["tendenza.minimo_20g"] == closes[-21]


def test_the_last_close_comes_with_its_instant_in_utc() -> None:
    values = long_trend(daily(rising(61)))

    assert values["tendenza.ultima_chiusura"] == Decimal(160)
    assert values["tendenza.ultima_chiusura_istante"] == "2026-11-21T00:00:00+00:00"
    assert "tendenza.dati_mancanti" not in values


def test_an_instant_in_another_zone_is_written_in_utc() -> None:
    zone = datetime(2026, 11, 21, 1, tzinfo=UTC).astimezone().tzinfo
    [candle] = daily([Decimal(5)])
    shifted = Candle(candle.closed_at.astimezone(zone), candle.close, candle.volume, candle.high, candle.low)

    assert long_trend([shifted])["tendenza.ultima_chiusura_istante"] == "2026-11-21T00:00:00+00:00"


def test_a_horizon_without_enough_history_is_declared_missing() -> None:
    values = long_trend(daily(rising(20)))

    assert {"tendenza.variazione_7g", "tendenza.variazione_14g", "tendenza.ultima_chiusura"} <= set(values)
    assert not {
        "tendenza.variazione_30g",
        "tendenza.variazione_60g",
        "tendenza.massimo_20g",
        "tendenza.minimo_20g",
    } & set(values)
    assert values["tendenza.dati_mancanti"] == (
        "variazione_30g, variazione_60g, massimo_20g, minimo_20g: storico di 20 giorni chiusi"
    )


@pytest.mark.parametrize(
    ("count", "missing"),
    [
        (61, None),
        (60, "variazione_60g: storico di 60 giorni chiusi"),
        (21, "variazione_30g, variazione_60g: storico di 21 giorni chiusi"),
        (8, "variazione_14g, variazione_30g, variazione_60g, massimo_20g, minimo_20g: storico di 8 giorni chiusi"),
        (
            1,
            "variazione_7g, variazione_14g, variazione_30g, variazione_60g, massimo_20g, minimo_20g: "
            "storico di 1 giorni chiusi",
        ),
    ],
)
def test_each_value_needs_its_own_history(count: int, missing: str | None) -> None:
    assert long_trend(daily(rising(count))).get("tendenza.dati_mancanti") == missing


def test_without_daily_candles_every_value_is_missing() -> None:
    assert long_trend([]) == {
        "tendenza.dati_mancanti": (
            "variazione_7g, variazione_14g, variazione_30g, variazione_60g, massimo_20g, minimo_20g, ultima_chiusura: "
            "storico di 0 giorni chiusi"
        )
    }
