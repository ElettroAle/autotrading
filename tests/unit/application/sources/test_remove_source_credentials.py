import pytest

from autotrading.application.sources.errors import SourceCredentialsNotFoundError
from autotrading.application.sources.remove_source_credentials import (
    RemoveSourceCredentialsCommand,
    RemoveSourceCredentialsUseCase,
)
from tests.support.source_keys import PAID, Keys


def test_removing_the_credentials_leaves_the_adapter_not_configured() -> None:
    keys = Keys()
    keys.configure_paid()

    RemoveSourceCredentialsUseCase(keys.credentials).execute(RemoveSourceCredentialsCommand(PAID))

    assert not keys.listing.execute()[0].configured


def test_removing_credentials_never_given_is_not_found() -> None:
    with pytest.raises(SourceCredentialsNotFoundError, match="credenziali dell'adapter non trovate: Pagato") as raised:
        RemoveSourceCredentialsUseCase(Keys().credentials).execute(RemoveSourceCredentialsCommand(PAID))

    assert raised.value.status_code == 404
