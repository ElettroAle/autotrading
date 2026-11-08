from autotrading.domain.errors import AutotradingError, DomainError


def test_domain_error_is_a_platform_error() -> None:
    assert issubclass(DomainError, AutotradingError)


def test_platform_error_is_not_a_system_error_subclass_beyond_exception() -> None:
    assert AutotradingError.__bases__ == (Exception,)
