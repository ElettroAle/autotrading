from datetime import datetime

from autotrading.application.flows.ports import (
    ClockPort,
    LossReferencesPort,
    OpeningsSuspendedNoticePort,
    OpeningsSuspensionPort,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.loss_guard import LossGuard
from autotrading.domain.flows.openings_suspension import OpeningsStatus, OpeningsSuspension, day_start


class GuardFlowLossUseCase:
    """The losses of the flow of the cycle against its thresholds, at the risk step, before the risk check (R3.2.2).

    A suspension ended on its own the next day is lifted first, at its midnight; openings still suspended stay so
    without a new notice. Otherwise the value read now is measured from the recorded equities: the first threshold
    passed suspends the openings and tells the user once (ADR perdita-massima-sui-valori-di-equity-registrati).
    """

    def __init__(
        self,
        openings: OpeningsSuspensionPort,
        references: LossReferencesPort,
        notices: OpeningsSuspendedNoticePort,
        clock: ClockPort,
    ) -> None:
        self._openings = openings
        self._references = references
        self._notices = notices
        self._clock = clock

    def execute(self, flow: CycleFlow) -> OpeningsSuspension | None:
        now = self._clock.now()
        status = self._status_at(flow, now)
        if status.suspension is not None:
            return status.suspension
        breach = self._breach(flow, status, now)
        if breach is None:
            return None
        suspension = OpeningsSuspension(breach, now)
        self._openings.suspend(flow.flow.id.value, suspension)
        self._notices.execute(flow.flow.name.value, breach)
        return suspension

    def _status_at(self, flow: CycleFlow, now: datetime) -> OpeningsStatus:
        flow_id, resume = flow.flow.id.value, flow.configuration.openings_resume
        saved = self._openings.status(flow_id)
        ended_at = saved.ended_at(now, resume)
        if ended_at is not None:
            self._openings.resume(flow_id, ended_at)
        return saved.at(now, resume)

    def _breach(self, flow: CycleFlow, status: OpeningsStatus, now: datetime) -> str | None:
        configuration = flow.configuration
        if configuration.max_daily_loss_percent is None and configuration.max_drawdown_percent is None:
            return None
        peak_since = status.peak_since(flow.started_at)
        references = self._references.loss_references(flow.flow.id.value, day_start(now), peak_since)
        return LossGuard.of(configuration, flow.total_value, references).breach()
