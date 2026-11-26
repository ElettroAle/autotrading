from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.application.flows.ports import (
    AccountExecutionsRecorderPort,
    CycleFlowReaderPort,
    FlowLossGuardPort,
    OpeningBlockedNoticePort,
    OpeningReducedNoticePort,
    OrderPort,
    ReversedExecutions,
)
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowCommand
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsCommand
from autotrading.application.flows.transient_retry import TransientRetry
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.cycle_record import FailedAttempt
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.opening_review import blocked_openings, reduced_openings
from autotrading.domain.flows.risk_outcome import ApprovedClose, BlockedDecision, RiskOutcome, approved_of
from autotrading.domain.flows.trade_intent import OpenIntent


class ReverseCyclePositionsUseCase:
    """The second step of the reversals of a cycle, after its orders are sent (R1.4.10, ADR
    inversione-in-due-passi-nel-ciclo).

    The account is reconciled first, so the money and the liquidity of the flow count the result of the closes. An
    opening whose close the exchange did not execute is never sent; the others are checked as every opening, on the
    state read again, with the guard of the losses and the notices of the openings reduced or blocked (R3.2.2, R3.5.1),
    and sent with the configuration read at the start of the cycle.

    A temporary error of the readings after the closes and of the check is retried in the same cycle, the orders are
    sent again by the orders context alone (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo).
    """

    def __init__(  # noqa: PLR0913, PLR0917 - the readings after the close, the check of the openings, their sending, retry
        self,
        record_executions: AccountExecutionsRecorderPort,
        read_flow: CycleFlowReaderPort,
        check_risk: CheckRiskUseCase,
        loss_guard: FlowLossGuardPort,
        reduced_notice: OpeningReducedNoticePort,
        blocked_notice: OpeningBlockedNoticePort,
        send_orders: OrderPort[CycleOrder, object],
        retry: TransientRetry,
    ) -> None:
        self._record_executions = record_executions
        self._read_flow = read_flow
        self._check_risk = check_risk
        self._loss_guard = loss_guard
        self._reduced_notice = reduced_notice
        self._blocked_notice = blocked_notice
        self._send_orders = send_orders
        self._retry = retry

    def execute(
        self, flow_id: UUID, planned_at: datetime, anchor: datetime, orders: Sequence[CycleOrder]
    ) -> ReversedExecutions[object]:
        openings = _reopenings_of(orders)
        if not openings:
            return ReversedExecutions((), ())
        failed: list[FailedAttempt] = []
        flow = self._retried(lambda: self._flow_after_closes(orders[0].flow, anchor), failed)
        outcomes = self._outcomes(flow, openings, failed)
        approved = tuple(CycleOrder(flow, outcome) for outcome in approved_of(outcomes))
        if not approved:
            return ReversedExecutions((), outcomes, tuple(failed))
        executions = tuple(self._send_orders.execute(flow_id, planned_at, approved))
        return ReversedExecutions(executions, outcomes, tuple(failed))

    def _retried[T](self, call: Callable[[], T], failed: list[FailedAttempt]) -> T:
        """The reversals are the second part of the execution of the orders (ADR inversione-in-due-passi-nel-ciclo)."""
        return self._retry.run(
            call, lambda attempt, error: failed.append(FailedAttempt.of(CycleStep.ORDER_EXECUTION, attempt, error))
        )

    def _flow_after_closes(self, started: CycleFlow, anchor: datetime) -> CycleFlow:
        """The account and the state now, with the configuration the cycle read at its start (R1.1.3)."""
        self._record_executions.execute(RecordAccountExecutionsCommand(started.flow.assigned_account_id))
        read = self._read_flow.execute(ReadCycleFlowCommand(started.flow.id, anchor, reconciled=False))
        return replace(
            started,
            account=read.account,
            attributed=read.attributed,
            alarm=read.alarm,
            account_exposure=read.account_exposure,
        )

    def _outcomes(
        self, flow: CycleFlow, openings: tuple[OpenIntent, ...], failed: list[FailedAttempt]
    ) -> tuple[RiskOutcome, ...]:
        still_open = {position.asset for position in flow.positions}
        not_closed = tuple(opening for opening in openings if opening.asset in still_open)
        closed = tuple(opening for opening in openings if opening.asset not in still_open)
        checked = self._retried(lambda: self._checked(flow, closed), failed)
        outcomes = {
            **{opening.asset: BlockedDecision.closing_not_executed(opening.asset) for opening in not_closed},
            **{outcome.asset: outcome for outcome in checked},
        }
        return tuple(outcomes[opening.asset] for opening in openings)

    def _checked(self, flow: CycleFlow, openings: tuple[OpenIntent, ...]) -> tuple[RiskOutcome, ...]:
        if not openings:
            return ()
        loss_suspension = self._loss_guard.execute(flow)
        command = CheckRiskCommand(
            openings,
            flow.configuration.risk_policy,
            flow.risk_state(loss_suspension=loss_suspension),
            flow.exchange,
        )
        outcomes = self._check_risk.execute(command)
        self._tell_openings(flow, command, outcomes)
        return outcomes

    def _tell_openings(self, flow: CycleFlow, command: CheckRiskCommand, outcomes: tuple[RiskOutcome, ...]) -> None:
        flow_id, flow_name = flow.flow.id.value, flow.flow.name.value
        for reduction in reduced_openings(command.intents, outcomes, command.state.funds):
            self._reduced_notice.execute(
                flow_id, flow_name, reduction.asset, reduction.requested_margin, reduction.approved_margin
            )
        for blocked in blocked_openings(command.intents, outcomes):
            self._blocked_notice.execute(flow_id, flow_name, blocked.asset, blocked.cause)


def _reopenings_of(orders: Sequence[CycleOrder]) -> tuple[OpenIntent, ...]:
    return tuple(
        order.outcome.reopening
        for order in orders
        if isinstance(order.outcome, ApprovedClose) and order.outcome.reopening is not None
    )
