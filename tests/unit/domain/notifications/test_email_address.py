import pytest

from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import InvalidEmailAddressError
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


@pytest.mark.parametrize("text", ["anna@example.com", "  anna@example.com  ", "anna.rossi+flussi@posta.example.it"])
def test_an_address_with_the_form_of_an_email_is_accepted_without_the_spaces_around(text: str) -> None:
    assert EmailAddress.parse(text).value == text.strip()


@pytest.mark.parametrize(
    "text", ["anna", "anna@", "@example.com", "anna@example", "anna @example.com", "anna@@example.com", "", "   "]
)
def test_an_address_without_the_form_of_an_email_is_refused(text: str) -> None:
    with pytest.raises(InvalidEmailAddressError, match=r"^indirizzo email non valido$") as raised:
        EmailAddress.parse(text)

    assert raised.value.status_code == 400
    assert raised.value.details == {"address": text.strip()}


def test_an_address_never_exists_without_the_form_of_an_email() -> None:
    with pytest.raises(InvalidEmailAddressError):
        EmailAddress("anna")


@pytest.mark.parametrize(("text", "accepted"), [("anna@example.com", True), ("anna@", False), (" anna@x.it", False)])
def test_the_form_is_told_without_raising(text: str, accepted: bool) -> None:
    assert EmailAddress.accepts(text) is accepted


def test_the_address_of_the_notifications_belongs_to_its_tenant() -> None:
    tenant = TenantId.new()

    email = NotificationEmail(tenant, EmailAddress.parse("anna@example.com"))

    assert email.tenant_id == tenant
    assert isinstance(email, TenantOwned)
