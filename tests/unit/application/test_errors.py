from uuid import uuid4

import pytest

from autotrading.application.agent.errors import (
    ModelCreditExhaustedError,
    ModelKeyMissingError,
    ModelKeyRejectedError,
    ProviderKeyNotOpenedError,
)
from autotrading.application.errors import ApplicationError
from autotrading.application.flows.errors import FlowCredentialsRejectedError, FlowLedgerIncompleteError
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.errors import AutotradingError, DomainError, ErrorScope

ACCOUNT = uuid4()
OPENROUTER = ProviderName("openrouter")


def test_application_error_is_a_platform_error() -> None:
    assert issubclass(ApplicationError, AutotradingError)


def test_application_error_is_not_a_domain_error() -> None:
    assert not issubclass(ApplicationError, DomainError)


@pytest.mark.parametrize(
    "error",
    [
        ModelKeyRejectedError(OPENROUTER),
        ModelCreditExhaustedError(OPENROUTER),
        ModelKeyMissingError(OPENROUTER),
        ProviderKeyNotOpenedError(OPENROUTER),
    ],
)
def test_an_error_of_the_key_of_a_provider_concerns_the_provider(error: AutotradingError) -> None:
    assert error.scope == ErrorScope(provider="openrouter")


@pytest.mark.parametrize("error", [FlowCredentialsRejectedError("test-1", ACCOUNT), FlowLedgerIncompleteError(ACCOUNT)])
def test_an_error_of_the_account_concerns_the_account(error: AutotradingError) -> None:
    assert error.scope == ErrorScope(account_id=ACCOUNT)
