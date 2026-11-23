from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import TimeframeNotAvailableError
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.long_trend import (
    CHANNEL_DAYS,
    DAILY_TIMEFRAME,
    TREND_DAYS,
    LongTrendChoice,
    daily_timeframe_of,
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


def trend(days: tuple[int, ...] = (), channels: tuple[int, ...] = ()) -> LongTrendChoice:
    return LongTrendChoice(days, channels)


# The parameters


def test_the_days_of_the_changes_and_of_the_channels_are_lists_off_by_default() -> None:
    assert [
        (p.key, p.label, p.default, p.minimum, p.maximum, p.maximum_values) for p in (TREND_DAYS, CHANNEL_DAYS)
    ] == [
        ("tendenza_giorni", "tendenza giorni", (), 1, 3650, 8),
        ("canale_giorni", "canale giorni", (), 2, 3650, 8),
    ]
    assert {TREND_DAYS, CHANNEL_DAYS} <= set(INDICATORS.parameters)


def test_a_choice_follows_the_settings_and_the_defaults() -> None:
    assert LongTrendChoice.of({"tendenza_giorni": (3, 90), "canale_giorni": (10,)}) == trend((3, 90), (10,))
    assert LongTrendChoice.of({}) == trend()


@pytest.mark.parametrize(("chosen", "active"), [(trend(), False), (trend((7,)), True), (trend(channels=(20,)), True)])
def test_the_trend_is_active_with_at_least_one_value(chosen: LongTrendChoice, active: bool) -> None:
    assert chosen.active is active


@pytest.mark.parametrize(
    ("chosen", "candles"), [(trend((3, 90)), 91), (trend((7,), (20,)), 21), (trend(channels=(120,)), 121)]
)
def test_the_daily_candles_read_are_the_ones_the_longest_value_needs(chosen: LongTrendChoice, candles: int) -> None:
    assert chosen.daily_candles == candles


def test_the_daily_timeframe_is_one_the_market_publishes() -> None:
    assert daily_timeframe_of((Timeframe(240), Timeframe(1440))) == Timeframe(1440) == DAILY_TIMEFRAME


def test_a_market_without_daily_candles_has_no_long_trend() -> None:
    with pytest.raises(TimeframeNotAvailableError) as raised:
        daily_timeframe_of((Timeframe(240), Timeframe(10080)))

    assert raised.value.cycle_minutes == 1440


# The values


def test_the_change_compares_the_last_close_with_the_one_n_days_before() -> None:
    closes = [Decimal(52000)] * 31
    closes[0], closes[-1] = Decimal(50000), Decimal(55000)

    values = trend((7, 30)).values(daily(closes)).values

    assert values["tendenza.variazione_30g"] == Decimal(10)
    assert values["tendenza.variazione_7g"] == (Decimal(55000) / Decimal(52000) - 1) * 100


def test_every_day_chosen_has_its_own_change_and_no_other() -> None:
    closes = rising(91)

    values = trend((3, 90)).values(daily(closes)).values

    assert {key for key in values if "variazione" in key} == {"tendenza.variazione_3g", "tendenza.variazione_90g"}
    assert values["tendenza.variazione_3g"] == (closes[-1] / closes[-4] - 1) * 100


def test_the_channel_gives_highest_lowest_and_middle_of_the_closes_of_the_n_days_before_the_last() -> None:
    closes = [Decimal(100)] * 21
    closes[0], closes[5], closes[-1] = Decimal(90), Decimal(110), Decimal(1000)

    values = trend(channels=(20,)).values(daily(closes)).values

    assert (values["tendenza.massimo_20g"], values["tendenza.minimo_20g"], values["tendenza.punto_medio_20g"]) == (
        Decimal(110),
        Decimal(90),
        Decimal(100),
    )


def test_the_last_close_comes_with_its_instant_in_utc() -> None:
    computed = trend((7,)).values(daily(rising(8)))

    assert computed.values["tendenza.ultima_chiusura"] == Decimal(107)
    assert computed.values["tendenza.ultima_chiusura_istante"] == "2026-11-21T00:00:00+00:00"
    assert computed.missing == ()


def test_an_instant_in_another_zone_is_written_in_utc() -> None:
    zone = datetime(2026, 11, 21, 1, tzinfo=UTC).astimezone().tzinfo
    [candle] = daily([Decimal(5)])
    shifted = Candle(candle.closed_at.astimezone(zone), candle.close, candle.volume, candle.high, candle.low)

    assert trend((7,)).values([shifted]).values["tendenza.ultima_chiusura_istante"] == "2026-11-21T00:00:00+00:00"


def test_a_value_without_enough_history_is_declared_missing_and_the_others_arrive() -> None:
    computed = trend((7, 90), (10, 40)).values(daily(rising(40)))

    assert {"tendenza.variazione_7g", "tendenza.massimo_10g", "tendenza.ultima_chiusura"} <= set(computed.values)
    assert not {"tendenza.variazione_90g", "tendenza.massimo_40g"} & set(computed.values)
    assert computed.missing_note() == {
        "dati_mancanti": "tendenza.variazione_90g, tendenza.canale_40g: storico di 40 giorni chiusi"
    }


def test_without_daily_candles_every_value_is_missing() -> None:
    computed = trend((7,), (20,)).values([])

    assert computed.values == {}
    assert computed.missing_note() == {
        "dati_mancanti": (
            "tendenza.variazione_7g, tendenza.canale_20g, tendenza.ultima_chiusura: storico di 0 giorni chiusi"
        )
    }
