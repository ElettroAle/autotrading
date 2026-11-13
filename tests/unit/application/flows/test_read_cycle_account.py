"""The account of the flow as a cycle reads it on the exchange, proving its credentials (R1.2.4)."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import (
    FlowCredentialsNotOpenedError,
    FlowCredentialsRefusedError,
    FlowCredentialsRejectedError,
    FlowExchangeUnavailableError,
)
from autotrading.application.flows.read_cycle_account import CycleAccountReading, ReadCycleAccountUseCase
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.tenancy.tenant_id import TenantId

ACCOUNT_ID = uuid4()
SEALED = SealedAddress(TenantId.new(), ACCOUNT_ID, "Hyperliquid", 1, b"sealed")
ACCESS = CycleAccess("0xabc", "0xsecret")
ACCOUNT = CycleAccount("USDC", Decimal(100), ())


class Accounts:
    def sealed_address(self, account_id: UUID) -> SealedAddress:
        assert account_id == ACCOUNT_ID
        return SEALED

    def account_name(self, account_id: UUID) -> str:
        assert account_id == ACCOUNT_ID
        return "test-1"


class Opener:
    def __init__(self, error: AutotradingError | None = None) -> None:
        self.error = error

    def open_cycle_access(self, sealed: SealedAddress) -> CycleAccess:
        assert sealed == SEALED
        if self.error is not None:
            raise self.error
        return ACCESS


class Reader:
    def __init__(self, error: AutotradingError | None = None) -> None:
        self.error = error

    def cycle_reading(self, access: CycleAccess) -> CycleAccount:
        assert access == ACCESS
        if self.error is not None:
            raise self.error
        return ACCOUNT


def use_case(opener: Opener | None = None, reader: Reader | None = None) -> ReadCycleAccountUseCase:
    accounts = Accounts()
    return ReadCycleAccountUseCase(accounts, accounts, opener or Opener(), {"Hyperliquid": reader or Reader()})


def test_the_account_is_read_with_its_name_and_exchange() -> None:
    assert use_case().execute(ACCOUNT_ID) == CycleAccountReading("test-1", "Hyperliquid", ACCOUNT)


@pytest.mark.parametrize(
    ("opener", "reader"),
    [(Opener(FlowCredentialsNotOpenedError()), Reader()), (Opener(), Reader(FlowCredentialsRefusedError()))],
)
def test_credentials_not_opened_or_refused_are_a_rejection_of_the_account(opener: Opener, reader: Reader) -> None:
    with pytest.raises(FlowCredentialsRejectedError) as raised:
        use_case(opener, reader).execute(ACCOUNT_ID)

    assert raised.value.scope.account_id == ACCOUNT_ID
    assert raised.value.permanent


def test_an_exchange_without_reader_is_unavailable() -> None:
    accounts = Accounts()

    with pytest.raises(FlowExchangeUnavailableError):
        ReadCycleAccountUseCase(accounts, accounts, Opener(), {}).execute(ACCOUNT_ID)


def test_an_exchange_that_does_not_answer_fails_the_cycle_without_rejecting_the_account() -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        use_case(reader=Reader(FlowExchangeUnavailableError())).execute(ACCOUNT_ID)
