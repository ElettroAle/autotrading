from autotrading.domain.errors import AutotradingError, DomainError


def test_domain_error_is_a_platform_error() -> None:
    assert issubclass(DomainError, AutotradingError)


def test_platform_error_is_not_a_system_error_subclass_beyond_exception() -> None:
    assert AutotradingError.__bases__ == (Exception,)


def test_a_platform_error_is_answered_as_a_bad_request_unless_it_says_otherwise() -> None:
    assert AutotradingError.status_code == 400


def test_a_platform_error_is_transient_unless_it_says_otherwise() -> None:
    assert AutotradingError.permanent is False


def test_a_platform_error_adds_nothing_to_its_reason_unless_it_says_otherwise() -> None:
    assert AutotradingError("motivo").details == {}
