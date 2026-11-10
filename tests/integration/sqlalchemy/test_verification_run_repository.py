from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, RowMapping, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import verification_runs
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.verification_run_repository import (
    SqlAlchemyVerificationRunRepositoryAdapter,
)
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.procedure import Step
from autotrading.domain.verification.step_outcome import StepOutcome
from autotrading.domain.verification.verification_run import VerificationRun
from tests.support.accounts import an_account
from tests.support.verification import OPENED, REFUSED, STARTED_AT, passed_steps

pytestmark = pytest.mark.integration


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def a_run_on(account_id: UUID, *steps: StepOutcome) -> VerificationRun:
    return VerificationRun(uuid4(), account_id, "oid-anna", "dev", STARTED_AT, steps or passed_steps())


def rows_of(database: Engine, tenant_id: TenantId | None) -> list[RowMapping]:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(verification_runs)).mappings())


def test_a_passed_run_is_recorded_with_user_account_environment_instant_and_outcome(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    run = a_run_on(account_id)

    SqlAlchemyVerificationRunRepositoryAdapter(database, tenant_id).add(run)

    (row,) = rows_of(database, tenant_id)
    assert (row["id"], row["account_id"], row["user_id"], row["environment"]) == (run.id, account_id, "oid-anna", "dev")
    assert (row["started_at"], row["outcome"], row["warning"]) == (STARTED_AT, "superata", None)
    assert (row["total_fee"], row["realized_pnl"]) == (Decimal("0.0109"), Decimal("-0.012"))


def test_each_step_is_recorded_with_what_it_read_or_what_its_order_did(database: Engine) -> None:
    tenant_id, account_id = new_account(database)

    SqlAlchemyVerificationRunRepositoryAdapter(database, tenant_id).add(a_run_on(account_id))

    (row,) = rows_of(database, tenant_id)
    opening, after_opening, _, after_closing = row["steps"]
    assert opening == {
        "step": "apertura long BTC leva 2",
        "succeeded": True,
        "message": None,
        "reading": None,
        "order": {"succeeded": True, "fee": "0.0054", "realized_pnl": "0", "message": None},
    }
    assert after_opening["reading"] == {
        "balance": "250.5",
        "available_margin": "100",
        "currency": "USDC",
        "positions": [{"coin": "BTC", "side": "long", "size": "0.00012", "leverage": 2}],
    }
    assert after_closing["reading"]["positions"] == []


def test_a_failed_run_is_recorded_with_the_step_where_it_stopped_and_its_warning(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    steps = (
        StepOutcome(Step.OPENING, succeeded=True, order=OPENED),
        StepOutcome(Step.READING_AFTER_OPENING, succeeded=True, reading=passed_steps()[1].reading),
        StepOutcome(Step.CLOSING, succeeded=False, message=REFUSED.message, order=REFUSED),
    )

    SqlAlchemyVerificationRunRepositoryAdapter(database, tenant_id).add(a_run_on(account_id, *steps))

    (row,) = rows_of(database, tenant_id)
    assert (row["outcome"], row["warning"]) == (
        "fallita al passo chiusura",
        "sul conto resta aperta una posizione long su BTC",
    )
    assert row["steps"][-1]["message"] == REFUSED.message


def test_the_runs_of_a_tenant_are_invisible_to_another_and_without_a_tenant(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    SqlAlchemyVerificationRunRepositoryAdapter(database, anna).add(a_run_on(account_id))

    assert (len(rows_of(database, bruno)), len(rows_of(database, None))) == (0, 0)


def test_a_run_on_an_account_of_another_tenant_cannot_be_written(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)

    with pytest.raises(IntegrityError, match="verification_runs_account_of_tenant"):
        SqlAlchemyVerificationRunRepositoryAdapter(database, bruno).add(a_run_on(account_id))

    assert (rows_of(database, anna), rows_of(database, bruno)) == ([], [])


def test_the_application_cannot_change_a_recorded_run(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    SqlAlchemyVerificationRunRepositoryAdapter(database, tenant_id).add(a_run_on(account_id))

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        with pytest.raises(ProgrammingError, match="permission denied"):
            connection.execute(text("UPDATE verification_runs SET outcome = 'superata'"))
