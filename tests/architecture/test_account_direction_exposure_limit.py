"""ADR-esposizione-massima-per-direzione-del-conto: the account holds an optional percent with its invariant in the
domain; one use case of the accounts context sets or removes it and the reading of the accounts returns it; an optional
column of the accounts, with no value for the accounts that existed; the API reads and changes it, the MCP tools only
read it.
"""

import inspect
import re
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from typing import get_type_hints

from autotrading.adapters.inbound.api import accounts as api_accounts
from autotrading.adapters.inbound.mcp import reading_views
from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.set_max_direction_exposure import SetMaxDirectionExposureUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.errors import MaxDirectionExposureNotPositiveError
from autotrading.domain.errors import DomainError

MCP = Path(inspect.getfile(reading_views)).parent
MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0061_account_direction_exposure.py"
# A tool that changes the limit: the tools only read it.
WRITING_TOOL = re.compile(r"set_max_direction_exposure|with_max_direction_exposure")
# A value given to the accounts that existed: they read the limit empty.
VALUE_FOR_THE_EXISTING = re.compile(r"server_default|nullable=False|op\.execute|UPDATE ")


def mcp_writes_the_limit(source: str) -> bool:
    return WRITING_TOOL.search(source) is not None


def migration_gives_a_value(source: str) -> bool:
    return VALUE_FOR_THE_EXISTING.search(source) is not None


def test_adr_esposizione_massima_per_direzione_the_account_holds_an_optional_percent_checked_by_the_domain() -> None:
    field = next(field for field in fields(Account) if field.name == "max_direction_exposure_percent")

    assert get_type_hints(Account)["max_direction_exposure_percent"] == Decimal | None
    assert field.default is None
    assert issubclass(MaxDirectionExposureNotPositiveError, DomainError)
    assert "MaxDirectionExposureNotPositiveError" in inspect.getsource(Account.__post_init__)


def test_adr_esposizione_massima_per_direzione_one_use_case_sets_it_and_the_reading_returns_it() -> None:
    assert SetMaxDirectionExposureUseCase.__module__ == "autotrading.application.accounts.set_max_direction_exposure"
    assert "max_direction_exposure_percent" in {field.name for field in fields(AccountSummary)}
    assert "set_max_direction_exposure.execute" in inspect.getsource(api_accounts)


def test_adr_esposizione_massima_per_direzione_the_tools_only_read_it_and_the_column_starts_empty() -> None:
    tools = "\n".join(path.read_text(encoding="utf-8") for path in sorted(MCP.glob("*.py")))
    migration = MIGRATION.read_text(encoding="utf-8")

    assert "max_direction_exposure_percent" in tools
    assert not mcp_writes_the_limit(tools)
    assert "nullable=True" in migration
    assert not migration_gives_a_value(migration)


def test_adr_esposizione_massima_per_direzione_a_tool_that_writes_and_a_value_for_the_existing_are_found() -> None:
    assert mcp_writes_the_limit("use_cases().set_max_direction_exposure.execute(command)")
    assert migration_gives_a_value('sa.Column("max_direction_exposure_percent", sa.Numeric(), server_default="100")')
