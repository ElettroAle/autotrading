import pytest

from autotrading.domain.errors import AutotradingError, DomainError, ErrorScope


class ExternalRefusal(Exception):  # noqa: N818 - the error a library of an external system raises, not a project error
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


class ExternalResponse:
    def __init__(self, status_code: int | None) -> None:
        self.status_code = status_code


class ExternalHttpFailure(Exception):  # noqa: N818 - the error a library of an external system raises, not a project error
    def __init__(self, response: ExternalResponse | None) -> None:
        super().__init__("http failure")
        self.response = response


class DeclaredPermanentError(AutotradingError):
    declared_permanent = True


class ForbiddenAnswerError(AutotradingError):
    """A project error answered with 403: its own status is the answer of the platform, not of an external system."""

    status_code = 403


def caused_by(error: AutotradingError, cause: BaseException | None) -> AutotradingError:
    error.__cause__ = cause
    return error


def test_domain_error_is_a_platform_error() -> None:
    assert issubclass(DomainError, AutotradingError)


def test_platform_error_is_not_a_system_error_subclass_beyond_exception() -> None:
    assert AutotradingError.__bases__ == (Exception,)


def test_a_platform_error_is_answered_as_a_bad_request_unless_it_says_otherwise() -> None:
    assert AutotradingError.status_code == 400


def test_a_platform_error_declares_itself_transient_unless_it_says_otherwise() -> None:
    assert AutotradingError.declared_permanent is False


def test_a_platform_error_adds_nothing_to_its_reason_unless_it_says_otherwise() -> None:
    assert AutotradingError("motivo").details == {}


def test_a_platform_error_concerns_only_the_flow_of_its_cycle_unless_it_says_otherwise() -> None:
    assert AutotradingError("motivo").scope == ErrorScope()


# ADR permanenza-decisa-dall-errore-base: the base error decides the permanence from the code of the external system.


@pytest.mark.parametrize("status", [401, 402, 403])
def test_adr_permanence_a_blocking_external_code_is_permanent_even_if_the_error_does_not_declare_it(
    status: int,
) -> None:
    assert caused_by(AutotradingError("motivo"), ExternalRefusal(status)).permanent is True


@pytest.mark.parametrize("status", [429, 500, 502, 503, 599])
def test_adr_permanence_a_rate_limit_or_server_code_is_transient_even_if_the_error_declares_itself_permanent(
    status: int,
) -> None:
    assert caused_by(DeclaredPermanentError("motivo"), ExternalRefusal(status)).permanent is False


@pytest.mark.parametrize("declared", [AutotradingError, DeclaredPermanentError])
@pytest.mark.parametrize("status", [400, 404, 422, 600])
def test_adr_permanence_any_other_external_code_keeps_what_the_error_declares(
    declared: type[AutotradingError], status: int
) -> None:
    error = caused_by(declared("motivo"), ExternalRefusal(status))

    assert error.permanent is declared.declared_permanent


@pytest.mark.parametrize("declared", [AutotradingError, DeclaredPermanentError])
def test_adr_permanence_without_a_cause_the_error_keeps_what_it_declares(declared: type[AutotradingError]) -> None:
    assert declared("motivo").permanent is declared.declared_permanent


def test_adr_permanence_reads_the_code_of_the_response_of_the_cause() -> None:
    error = caused_by(DeclaredPermanentError("motivo"), ExternalHttpFailure(ExternalResponse(429)))

    assert error.permanent is False


@pytest.mark.parametrize("response", [None, ExternalResponse(None)])
def test_adr_permanence_a_cause_without_a_code_keeps_what_the_error_declares(response: ExternalResponse | None) -> None:
    error = caused_by(DeclaredPermanentError("motivo"), ExternalHttpFailure(response))

    assert error.permanent is True


def test_adr_permanence_follows_the_chain_of_causes_through_the_errors_of_the_project() -> None:
    translated = caused_by(AutotradingError("tradotto"), ExternalRefusal(429))

    assert caused_by(DeclaredPermanentError("motivo"), translated).permanent is False


def test_adr_permanence_ignores_the_status_a_project_error_answers_with() -> None:
    assert caused_by(AutotradingError("motivo"), ForbiddenAnswerError("vietato")).permanent is False


def test_adr_permanence_the_nearest_external_code_decides() -> None:
    nearest = caused_by(AutotradingError("tradotto"), ExternalRefusal(429))
    nearest.__cause__.__cause__ = ExternalRefusal(401)  # type: ignore[union-attr]  # the cause set just above

    assert caused_by(AutotradingError("motivo"), nearest).permanent is False


def test_adr_permanence_a_chain_of_causes_that_loops_ends_with_what_the_error_declares() -> None:
    first, second = AutotradingError("primo"), AutotradingError("secondo")
    first.__cause__, second.__cause__ = second, first

    assert caused_by(DeclaredPermanentError("motivo"), first).permanent is True
