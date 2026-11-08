from autotrading.application.errors import ApplicationError
from autotrading.domain.errors import AutotradingError, DomainError


def test_application_error_is_a_platform_error() -> None:
    assert issubclass(ApplicationError, AutotradingError)


def test_application_error_is_not_a_domain_error() -> None:
    assert not issubclass(ApplicationError, DomainError)
