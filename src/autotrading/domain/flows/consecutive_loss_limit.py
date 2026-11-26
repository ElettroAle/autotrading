from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from autotrading.domain.flows.errors import (
    BlockBelowOneMinuteError,
    ConsecutiveLossPartsApartError,
    LossCountScopeNotAllowedError,
    LossWindowBelowOneHourError,
    MaxConsecutiveLossesBelowOneError,
)
from autotrading.domain.flows.statistics_period import TimeWindow

FEWEST_LOSSES = 1
SHORTEST_WINDOW_HOURS = 1
SHORTEST_BLOCK_MINUTES = 1


class LossCountScope(StrEnum):
    """Where the losses are counted and the openings blocked: on each asset alone, or on every asset of the flow
    (R5.5.2). The values are the words the user gives them with.
    """

    ASSET = "asset"
    FLOW = "flusso"

    @classmethod
    def named(cls, name: str | None) -> LossCountScope:
        """The scope the user gave, the asset when none is given."""
        if name is None:
            return cls.ASSET
        scope = next((scope for scope in cls if scope.value == name), None)
        if scope is None:
            raise LossCountScopeNotAllowedError
        return scope


@dataclass(frozen=True, slots=True)
class ConsecutiveLossLimit:
    """How many losses in a row on one side block the openings on that side, within how many hours, for how many
    minutes, and whether they are counted on each asset or on the whole flow (R5.5.2, ADR
    limite-di-perdite-consecutive-del-flusso).

    The three numbers go together and are at least 1; a flow without the limit has none of them.
    """

    max_consecutive_losses: int
    loss_window_hours: int
    block_minutes: int
    count_scope: LossCountScope = LossCountScope.ASSET

    def __post_init__(self) -> None:
        if self.max_consecutive_losses < FEWEST_LOSSES:
            raise MaxConsecutiveLossesBelowOneError
        if self.loss_window_hours < SHORTEST_WINDOW_HOURS:
            raise LossWindowBelowOneHourError
        if self.block_minutes < SHORTEST_BLOCK_MINUTES:
            raise BlockBelowOneMinuteError

    @classmethod
    def of(
        cls,
        max_consecutive_losses: int | None,
        loss_window_hours: int | None,
        block_minutes: int | None,
        count_scope: str | None,
    ) -> ConsecutiveLossLimit | None:
        """The limit the user gave: none without any part, refused with only some of the three numbers or with a scope
        alone.
        """
        numbers = (max_consecutive_losses, loss_window_hours, block_minutes)
        if all(number is None for number in numbers) and count_scope is None:
            return None
        if max_consecutive_losses is None or loss_window_hours is None or block_minutes is None:
            raise ConsecutiveLossPartsApartError
        scope = LossCountScope.named(count_scope)
        return cls(max_consecutive_losses, loss_window_hours, block_minutes, scope)

    def window(self, at: datetime) -> TimeWindow:
        """The closings the losses are counted on: those of the last hours of the window, up to the instant."""
        return TimeWindow(at - timedelta(hours=self.loss_window_hours))

    @property
    def block_duration(self) -> timedelta:
        return timedelta(minutes=self.block_minutes)

    def counted_asset(self, asset: str) -> str | None:
        """The asset a closing counts on: its own, or None when every asset of the flow counts together."""
        return asset if self.count_scope is LossCountScope.ASSET else None

    def __str__(self) -> str:
        return (
            f"{self.max_consecutive_losses} perdite consecutive in {self.loss_window_hours} ore, blocco di "
            f"{self.block_minutes} minuti, ambito {self.count_scope.value}"
        )
