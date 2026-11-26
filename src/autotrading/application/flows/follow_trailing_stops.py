import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from autotrading.application.flows.ports import (
    AccountActivityPort,
    ClockPort,
    FlowLockPort,
    FlowOpeningsPort,
    FlowProtectionLevelsPort,
    FlowRepositoryPort,
    FlowStopMove,
    FlowStopMovePort,
    WatchedPositionsPort,
)
from autotrading.application.flows.transient_retry import TransientRetry
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.flows.watched_position import WatchedPosition

operations = logging.getLogger("autotrading.flows")

# Half the interval of the check, as a cycle retries within half its interval (ADR
# ritentativo-del-ciclo-entro-meta-dell-intervallo): an exchange still away is tried again at the next check.
RETRY_WINDOW = timedelta(seconds=30)


@dataclass(frozen=True, slots=True)
class FollowTrailingStopsCommand:
    """A check of the worker: the positions of every flow of the tenant whose stop follows the price, at the prices of
    now."""


@dataclass(frozen=True, slots=True)
class WatchedPositionReadings:
    """What the check reads of a flow: its positions on the exchange, the opening of each and the stop in force."""

    activity: AccountActivityPort
    openings: FlowOpeningsPort
    protection_levels: FlowProtectionLevelsPort


@dataclass(frozen=True, slots=True)
class StopMoves:
    """The move of a stop through the orders context, with the retry of its temporary errors and the clock that bounds
    it."""

    move: FlowStopMovePort
    retry: TransientRetry
    clock: ClockPort


class FollowTrailingStopsUseCase:
    """Watches the price of every open position of the active flows of the tenant whose stop follows it, between the
    cycles, and moves the stop closer to the price whenever the stop the platform computes lies closer than the one in
    force (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue).

    The best price and the largest unrealized profit of each position are kept from its opening; a flow without distance
    and breakeven reads no price, and its positions are forgotten, so they count again from the price of the moment the
    setting comes back. A flow whose cycle is running skips its turn: the next check tries again. A refusal of the
    exchange waits for the next cycle; a flow the exchange cannot answer for is recorded and leaves the others going.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        watched: WatchedPositionsPort,
        lock: FlowLockPort,
        readings: WatchedPositionReadings,
        moves: StopMoves,
    ) -> None:
        self._flows = flows
        self._watched = watched
        self._lock = lock
        self._readings = readings
        self._moves = moves

    def execute(self, command: FollowTrailingStopsCommand) -> None:  # noqa: ARG002 - a check carries no data
        following = [flow for flow in self._flows.list() if flow.configuration.trailing_stop.active]
        self._watched.keep_only([flow.id for flow in following])
        for flow in following:
            if flow.status is FlowStatus.ACTIVE and self._cycle_not_running(flow):
                self._follow_apart(flow)

    def _cycle_not_running(self, flow: Flow) -> bool:
        """The lock of the cycles is only asked, never kept: a cycle due now starts, and the check waits for the next
        turn when one is running."""
        with self._lock.hold(flow.id.value) as free:
            return free

    def _follow_apart(self, flow: Flow) -> None:
        try:
            self._follow(flow)
        except AutotradingError as error:
            operations.warning(
                "sorveglianza dello stop interrotta", extra={"flow_id": str(flow.id.value), "error": str(error)}
            )

    def _follow(self, flow: Flow) -> None:
        self._moves.retry.limit_to(self._moves.clock.now() + RETRY_WINDOW)
        activity = self._readings.activity.execute(flow.assigned_account_id)
        held = flow.configuration.held(activity.positions, lambda position: position.asset)
        watched = {position.asset: position for position in self._watched.watched_of(flow.id)}
        self._forget_closed(flow, watched, held)
        for position in held:
            self._follow_position(flow, position, watched.get(position.asset))

    def _forget_closed(self, flow: Flow, watched: dict[str, WatchedPosition], held: Sequence[AccountPosition]) -> None:
        for asset in watched.keys() - {position.asset for position in held}:
            self._watched.forget(flow.id, asset)

    def _follow_position(self, flow: Flow, position: AccountPosition, previous: WatchedPosition | None) -> None:
        opening = self._readings.openings.last_opening(flow.id, position.asset)
        seen = WatchedPosition.seen(
            previous,
            position.asset,
            None if opening is None else opening.end.at,
            position.side,
            position.entry_price,
            position.size,
            position.mark_price,
        )
        stop = self._stop_to_move(flow.configuration.trailing_stop, flow, position, seen)
        if stop is not None:
            seen = seen.moved(self._moved(flow, position.asset, stop))
        if seen != previous:
            self._watched.save(flow.id, seen)

    def _stop_to_move(
        self, trailing: TrailingStop, flow: Flow, position: AccountPosition, seen: WatchedPosition
    ) -> Decimal | None:
        in_force = self._readings.protection_levels.placed_levels(flow.id, position.asset).stop
        return trailing.moved_stop(position.side, position.entry_price, seen.best_price, in_force)

    def _moved(self, flow: Flow, asset: str, stop: Decimal) -> str | None:
        default_stop = flow.configuration.protection_defaults.stop_loss_percent
        return self._moves.move.execute(
            FlowStopMove(flow.assigned_account_id, flow.id.value, asset, stop, default_stop)
        )
