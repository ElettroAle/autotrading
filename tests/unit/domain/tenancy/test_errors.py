from autotrading.domain.errors import DomainError
from autotrading.domain.tenancy.errors import EmptyUserIdError


def test_tenancy_errors_are_domain_errors() -> None:
    assert issubclass(EmptyUserIdError, DomainError)
