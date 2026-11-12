from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from autotrading.application.verification.errors import VerificationStepError
from autotrading.application.verification.ports import (
    AccountReadingPort,
    OrderExecutionPort,
    VerificationRunRepositoryPort,
)
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import (
    PROCEDURE_OPENING,
    Step,
    missing_opening,
    remaining_position,
    require_free_of_flows,
    require_startable,
)
from autotrading.domain.verification.reading import AccountReading
from autotrading.domain.verification.step_outcome import StepOutcome
from autotrading.domain.verification.verification_run import VerificationRun


@dataclass(frozen=True, slots=True)
class RunExchangeVerificationCommand:
    account_id: UUID
    user_id: UserId


class RunExchangeVerificationUseCase:
    """In the worker: opens, reads, closes and reads again a position, and records each step (R0.4.1, ADR 0024).

    An account with a flow on the asset, a position on it, or without enough margin, does not start: nothing is sent
    or recorded. A flow on the asset would pause at its next cycle for the position the procedure changes (ADR 0075).
    Once started, the first step that fails stops the procedure; the steps already executed stay recorded.
    """

    def __init__(
        self,
        readings: AccountReadingPort,
        orders: OrderExecutionPort,
        runs: VerificationRunRepositoryPort,
        environment: str,
        clock: Callable[[], datetime],
    ) -> None:
        self._readings = readings
        self._orders = orders
        self._runs = runs
        self._environment = environment
        self._clock = clock

    def execute(self, command: RunExchangeVerificationCommand) -> VerificationRun:
        started_at = self._clock()
        require_free_of_flows(self._readings.flow_on(command.account_id, PROCEDURE_OPENING.coin))
        require_startable(self._readings.read(command.account_id))
        steps = self._steps_until_one_fails(command)
        run = VerificationRun(uuid4(), command.account_id, command.user_id.value, self._environment, started_at, steps)
        self._runs.add(run)
        return run

    def _steps_until_one_fails(self, command: RunExchangeVerificationCommand) -> tuple[StepOutcome, ...]:
        executed: list[StepOutcome] = []
        for step in Step:
            executed.append(self._step(step, command))
            if not executed[-1].succeeded:
                break
        return tuple(executed)

    def _step(self, step: Step, command: RunExchangeVerificationCommand) -> StepOutcome:
        account_id, user_id = command.account_id, command.user_id
        if step is Step.OPENING:
            return _order_step(step, lambda: self._orders.open(account_id, PROCEDURE_OPENING, user_id))
        if step is Step.READING_AFTER_OPENING:
            return _reading_step(step, lambda: self._readings.read(account_id), missing_opening)
        if step is Step.CLOSING:
            return _order_step(step, lambda: self._orders.close(account_id, PROCEDURE_OPENING.coin, user_id))
        return _reading_step(step, lambda: self._readings.read(account_id), remaining_position)


def _order_step(step: Step, send: Callable[[], OrderResult]) -> StepOutcome:
    try:
        result = send()
    except VerificationStepError as error:
        return StepOutcome(step, succeeded=False, message=error.message)
    return StepOutcome(step, succeeded=result.succeeded, message=result.message, order=result)


def _reading_step(
    step: Step, read: Callable[[], AccountReading], mismatch: Callable[[AccountReading], str | None]
) -> StepOutcome:
    try:
        reading = read()
    except VerificationStepError as error:
        return StepOutcome(step, succeeded=False, message=error.message)
    problem = mismatch(reading)
    return StepOutcome(step, succeeded=problem is None, message=problem, reading=reading)
