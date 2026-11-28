"""ADR-intervallo-di-riconciliazione-del-conto: a value object of the accounts domain, whole minutes from 1 to 1440
with the default of 5 as its constant, refused with the reason of the requirement; an optional column of the accounts
with no value for the accounts that existed; PUT /accounts/{id}/reconciliation-interval sets it and the reading of the
account always carries it; the flows context reads it through a port of its own, realized by the SQLAlchemy adapter;
the page of the account has the field with its info button and text.
"""

import inspect
import re
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

from autotrading.adapters.inbound.api import accounts as api_accounts
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.flows import ports as flow_ports
from autotrading.domain.accounts import reconciliation_interval
from autotrading.domain.accounts.errors import ReconciliationIntervalOutOfRangeError
from autotrading.domain.accounts.reconciliation_interval import ReconciliationInterval
from autotrading.domain.errors import DomainError

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "migrations" / "versions" / "0062_account_reconciliation_interval.py"
DASHBOARD = ROOT / "dashboard" / "src" / "features" / "accounts"
SETTINGS = DASHBOARD / "components" / "account-settings.tsx"
FORM = DASHBOARD / "components" / "reconciliation-interval-form.tsx"
INFO = DASHBOARD / "utils" / "setting-info.ts"
LABEL = "Intervallo di riconciliazione (minuti)"
# A value given to the accounts that existed: they read the column empty and the default of the domain applies.
VALUE_FOR_THE_EXISTING = re.compile(r"server_default|nullable=False|op\.execute|UPDATE ")


def migration_gives_a_value(source: str) -> bool:
    return VALUE_FOR_THE_EXISTING.search(source) is not None


def test_adr_intervallo_di_riconciliazione_a_value_object_from_1_to_1440_minutes_with_the_default_of_5() -> None:
    assert (reconciliation_interval.LOWEST_MINUTES, reconciliation_interval.HIGHEST_MINUTES) == (1, 1440)
    assert ReconciliationInterval.default() == ReconciliationInterval(5)
    assert issubclass(ReconciliationIntervalOutOfRangeError, DomainError)
    assert str(ReconciliationIntervalOutOfRangeError(0)) == "intervallo di riconciliazione da 1 a 1440 minuti"


def test_adr_intervallo_di_riconciliazione_the_column_starts_empty() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")

    assert '"reconciliation_interval_minutes"' in migration
    assert "nullable=True" in migration
    assert not migration_gives_a_value(migration)


def test_adr_intervallo_di_riconciliazione_a_value_for_the_existing_is_found() -> None:
    assert migration_gives_a_value('sa.Column("reconciliation_interval_minutes", sa.Integer(), server_default="5")')


def test_adr_intervallo_di_riconciliazione_the_api_sets_it_and_the_reading_always_carries_it() -> None:
    api = inspect.getsource(api_accounts)

    assert '@router.put("/{account_id}/reconciliation-interval"' in api
    assert "set_reconciliation_interval.execute" in api
    assert get_type_hints(AccountSummary)["reconciliation_interval_minutes"] is int
    assert "reconciliation_interval_minutes" in {field.name for field in fields(AccountSummary)}


def test_adr_intervallo_di_riconciliazione_the_flows_read_it_through_their_port_realized_by_sqlalchemy() -> None:
    port = flow_ports.AccountReconciliationIntervalPort

    assert port.__module__ == "autotrading.application.flows.ports"
    assert callable(SqlAlchemyAccountRepositoryAdapter.reconciliation_interval)
    assert get_type_hints(port.reconciliation_interval) == get_type_hints(
        SqlAlchemyAccountRepositoryAdapter.reconciliation_interval
    )


def test_adr_intervallo_di_riconciliazione_the_page_of_the_account_has_the_field_with_its_info() -> None:
    settings, form, info = (path.read_text(encoding="utf-8") for path in (SETTINGS, FORM, INFO))

    assert "<ReconciliationIntervalForm account={account} />" in settings
    assert f'label="{LABEL}"' in form
    assert "info={ACCOUNT_SETTING_INFO.reconciliationInterval}" in form
    assert re.search(r"reconciliationInterval:\s*\n?\s*['\"].*1 a 1440.*Predefinito: 5", info) is not None
