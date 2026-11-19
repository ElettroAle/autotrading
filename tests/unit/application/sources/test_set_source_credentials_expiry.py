from datetime import date

import pytest

from autotrading.application.sources.errors import SourceCredentialsNotFoundError
from autotrading.application.sources.set_source_credentials_expiry import (
    SetSourceCredentialsExpiryCommand,
    SetSourceCredentialsExpiryUseCase,
)
from autotrading.domain.sources.key_expiry import KeyExpiry
from tests.support.source_keys import PAID, Keys


def test_the_user_gives_and_forgets_the_expiry_of_the_credentials() -> None:
    keys = Keys()
    keys.configure_paid()
    set_expiry = SetSourceCredentialsExpiryUseCase(keys.credentials)

    set_expiry.execute(SetSourceCredentialsExpiryCommand(PAID, date(2027, 1, 10)))
    dated = keys.listing.execute()[0].expiry
    set_expiry.execute(SetSourceCredentialsExpiryCommand(PAID, None))

    assert dated == KeyExpiry.entered(date(2027, 1, 10))
    assert keys.listing.execute()[0].expiry is None


def test_the_expiry_of_credentials_never_given_is_not_found() -> None:
    with pytest.raises(SourceCredentialsNotFoundError):
        SetSourceCredentialsExpiryUseCase(Keys().credentials).execute(
            SetSourceCredentialsExpiryCommand(PAID, date(2027, 1, 10))
        )
