"""The procedure in progress, as PostgreSQL locks it for the worker and the API alike (ADR 0079)."""

from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.verification_locks import (
    SqlAlchemyRunningVerificationsAdapter,
    verification_lock_key,
)
from autotrading.adapters.outbound.sqlalchemy.verification_run_repository import (
    SqlAlchemyVerificationRunRepositoryAdapter,
)
from autotrading.application.flows.errors import AssetUnderVerificationError
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.verification.errors import VerificationInProgressError

pytestmark = pytest.mark.integration


class Interrupted(Exception):  # noqa: N818 - the failure a test raises inside the context, not a project error
    pass


def runs_of(database: Engine) -> SqlAlchemyVerificationRunRepositoryAdapter:
    return SqlAlchemyVerificationRunRepositoryAdapter(database, TenantId(uuid4()))


def test_a_second_procedure_on_the_asset_of_the_account_does_not_start_until_the_first_ends(database: Engine) -> None:
    account_id = uuid4()

    with runs_of(database).running(account_id, "BTC"):
        with pytest.raises(VerificationInProgressError) as raised, runs_of(database).running(account_id, "BTC"):
            pass
        assert str(raised.value) == "procedura di verifica già in corso su BTC"
        with runs_of(database).running(account_id, "ETH"), runs_of(database).running(uuid4(), "BTC"):
            pass

    with runs_of(database).running(account_id, "BTC"):
        pass


def test_a_procedure_that_fails_is_no_longer_in_progress(database: Engine) -> None:
    account_id = uuid4()

    with pytest.raises(Interrupted), runs_of(database).running(account_id, "BTC"):
        raise Interrupted

    with runs_of(database).running(account_id, "BTC"):
        pass


def test_a_flow_on_the_asset_does_not_start_while_the_procedure_runs_on_it(database: Engine) -> None:
    account_id, verifications = uuid4(), SqlAlchemyRunningVerificationsAdapter(database)

    with runs_of(database).running(account_id, "BTC"):
        with pytest.raises(AssetUnderVerificationError) as raised, verifications.kept_free(account_id, ["ETH", "BTC"]):
            pass
        assert str(raised.value) == "procedura di verifica in corso su BTC"
        with verifications.kept_free(account_id, ["ETH"]), verifications.kept_free(uuid4(), ["BTC"]):
            pass
        # The assets tried before the busy one are released with it: the procedure on ETH starts.
        with runs_of(database).running(account_id, "ETH"):
            pass

    with verifications.kept_free(account_id, ["ETH", "BTC"]):
        pass


def test_no_procedure_starts_on_the_assets_of_a_flow_while_its_status_changes(database: Engine) -> None:
    account_id, verifications = uuid4(), SqlAlchemyRunningVerificationsAdapter(database)

    with verifications.kept_free(account_id, ["BTC", "ETH"]):
        with pytest.raises(VerificationInProgressError), runs_of(database).running(account_id, "BTC"):
            pass
        with runs_of(database).running(account_id, "SOL"):
            pass

    with runs_of(database).running(account_id, "BTC"):
        pass


def test_the_key_tells_accounts_and_assets_apart_and_stays_the_same() -> None:
    account_id = uuid4()

    key = verification_lock_key(account_id, "BTC")

    assert key == verification_lock_key(account_id, "BTC")
    assert len({key, verification_lock_key(account_id, "ETH"), verification_lock_key(uuid4(), "BTC")}) == 3
    assert all(-(2**31) <= part < 2**31 for part in key)
