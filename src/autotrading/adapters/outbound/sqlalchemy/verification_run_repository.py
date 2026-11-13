from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.tables import verification_runs
from autotrading.adapters.outbound.sqlalchemy.verification_locks import verification_locks
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.verification.errors import VerificationInProgressError
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.reading import AccountReading
from autotrading.domain.verification.step_outcome import StepOutcome
from autotrading.domain.verification.verification_run import VerificationRun


class SqlAlchemyVerificationRunRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, run: VerificationRun) -> None:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            connection.execute(insert(verification_runs).values(_row_of(run, self._tenant_id)))

    @contextmanager
    def running(self, account_id: UUID, coin: str) -> Iterator[None]:
        # The same lock the API tries before a flow on the asset starts or resumes (ADR 0079).
        with verification_locks(self._engine, account_id, (coin,)) as busy:
            if busy is not None:
                raise VerificationInProgressError(busy)
            yield


def _row_of(run: VerificationRun, tenant_id: TenantId) -> dict[str, object]:
    return {
        "id": run.id,
        "tenant_id": tenant_id.value,
        "account_id": run.account_id,
        "user_id": run.user_id,
        "environment": run.environment,
        "started_at": run.started_at,
        "outcome": run.outcome,
        "total_fee": run.total_fee,
        "realized_pnl": run.realized_pnl,
        "warning": run.warning,
        "steps": [_step_of(outcome) for outcome in run.steps],
    }


def _step_of(outcome: StepOutcome) -> dict[str, object]:
    return {
        "step": outcome.step.value,
        "succeeded": outcome.succeeded,
        "message": outcome.message,
        "reading": None if outcome.reading is None else _reading_of(outcome.reading),
        "order": None if outcome.order is None else _order_of(outcome.order),
    }


def _reading_of(reading: AccountReading) -> dict[str, object]:
    # Amounts are kept as text, so no precision is lost in the JSON.
    return {
        "balance": str(reading.balance),
        "available_margin": str(reading.available_margin),
        "currency": reading.currency,
        "positions": [
            {"coin": p.coin, "side": p.side, "size": str(p.size), "leverage": p.leverage} for p in reading.positions
        ],
    }


def _order_of(result: OrderResult) -> dict[str, object]:
    return {
        "succeeded": result.succeeded,
        "fee": str(result.fee),
        "realized_pnl": str(result.realized_pnl),
        "message": result.message,
    }
