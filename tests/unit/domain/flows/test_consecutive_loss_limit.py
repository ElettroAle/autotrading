from datetime import UTC, datetime, timedelta

import pytest

from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit, LossCountScope
from autotrading.domain.flows.errors import (
    BlockBelowOneMinuteError,
    ConsecutiveLossPartsApartError,
    FlowSettingError,
    LossCountScopeNotAllowedError,
    LossWindowBelowOneHourError,
    MaxConsecutiveLossesBelowOneError,
)
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.statistics_period import TimeWindow

NOW = datetime(2026, 11, 26, 14, 0, tzinfo=UTC)


def test_the_limit_counts_on_each_asset_unless_the_user_says_otherwise() -> None:
    assert ConsecutiveLossLimit(2, 24, 120).count_scope is LossCountScope.ASSET


def test_nothing_given_is_no_limit() -> None:
    assert ConsecutiveLossLimit.of(None, None, None, None) is None


def test_the_three_numbers_without_a_scope_count_on_each_asset() -> None:
    assert ConsecutiveLossLimit.of(2, 24, 120, None) == ConsecutiveLossLimit(2, 24, 120, LossCountScope.ASSET)


@pytest.mark.parametrize(("name", "scope"), [("asset", LossCountScope.ASSET), ("flusso", LossCountScope.FLOW)])
def test_the_scope_is_the_word_the_user_gives(name: str, scope: LossCountScope) -> None:
    limit = ConsecutiveLossLimit.of(2, 24, 120, name)

    assert limit is not None
    assert limit.count_scope is scope


@pytest.mark.parametrize(
    ("losses", "hours", "minutes", "scope"),
    [(2, None, None, None), (None, 24, 120, None), (2, 24, None, "asset"), (None, None, None, "flusso")],
)
def test_refuses_some_of_the_three_numbers_or_a_scope_alone(
    losses: int | None, hours: int | None, minutes: int | None, scope: str | None
) -> None:
    reason = "perdite consecutive massime, finestra delle perdite e durata del blocco si impostano insieme"
    with pytest.raises(ConsecutiveLossPartsApartError, match=reason) as refused:
        ConsecutiveLossLimit.of(losses, hours, minutes, scope)

    assert refused.value.details == {"field": "consecutive_loss_limit.max_consecutive_losses"}


def test_refuses_a_scope_neither_asset_nor_flow_naming_the_setting() -> None:
    with pytest.raises(LossCountScopeNotAllowedError, match="l'ambito del conteggio è asset oppure flusso") as refused:
        ConsecutiveLossLimit.of(2, 24, 120, "conto")

    assert refused.value.setting is FlowSetting.LOSS_COUNT_SCOPE


@pytest.mark.parametrize(
    ("losses", "hours", "minutes", "error", "reason", "setting"),
    [
        (
            0,
            24,
            120,
            MaxConsecutiveLossesBelowOneError,
            "le perdite consecutive massime sono almeno 1",
            FlowSetting.MAX_CONSECUTIVE_LOSSES,
        ),
        (
            2,
            0,
            120,
            LossWindowBelowOneHourError,
            "la finestra delle perdite è di almeno 1 ora",
            FlowSetting.LOSS_WINDOW_HOURS,
        ),
        (
            2,
            24,
            0,
            BlockBelowOneMinuteError,
            "la durata del blocco è di almeno 1 minuto",
            FlowSetting.BLOCK_MINUTES,
        ),
    ],
)
def test_refuses_a_number_below_one_naming_its_setting(  # noqa: PLR0917 - one argument per column of the cases
    losses: int, hours: int, minutes: int, error: type[FlowSettingError], reason: str, setting: FlowSetting
) -> None:
    with pytest.raises(error, match=reason) as refused:
        ConsecutiveLossLimit(losses, hours, minutes)

    assert refused.value.setting is setting


def test_accepts_one_of_each() -> None:
    limit = ConsecutiveLossLimit(1, 1, 1)

    assert (limit.max_consecutive_losses, limit.loss_window_hours, limit.block_minutes) == (1, 1, 1)


def test_the_window_reaches_back_its_hours_from_the_instant() -> None:
    assert ConsecutiveLossLimit(2, 24, 120).window(NOW) == TimeWindow(NOW - timedelta(hours=24))


def test_the_block_lasts_its_minutes() -> None:
    assert ConsecutiveLossLimit(2, 24, 120).block_duration == timedelta(minutes=120)


def test_a_closing_counts_on_its_asset_with_the_scope_of_the_asset() -> None:
    assert ConsecutiveLossLimit(2, 24, 120, LossCountScope.ASSET).counted_asset("NEAR") == "NEAR"


def test_a_closing_counts_on_the_whole_flow_with_the_scope_of_the_flow() -> None:
    assert ConsecutiveLossLimit(2, 24, 120, LossCountScope.FLOW).counted_asset("NEAR") is None


def test_the_limit_reads_as_text_for_the_comparison_of_the_versions() -> None:
    text = str(ConsecutiveLossLimit(2, 24, 120, LossCountScope.FLOW))

    assert text == "2 perdite consecutive in 24 ore, blocco di 120 minuti, ambito flusso"
