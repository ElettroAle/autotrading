import json
import urllib.request
from collections.abc import Callable, Mapping

from autotrading.application.tenancy.errors import IdentityProviderUnavailableError

DIRECTORY_TIMEOUT_SECONDS = 5

type FetchJson = Callable[[str], Mapping[str, object]]


def discovery_url_of(issuer: str) -> str:
    return f"{issuer.rstrip('/')}/.well-known/openid-configuration"


def fetch_json(url: str) -> Mapping[str, object]:
    if not url.startswith("https://"):
        raise IdentityProviderUnavailableError
    with urllib.request.urlopen(url, timeout=DIRECTORY_TIMEOUT_SECONDS) as response:  # noqa: S310 - https only
        try:
            document: object = json.load(response)
        except ValueError as error:
            raise IdentityProviderUnavailableError from error
    if not isinstance(document, Mapping):
        raise IdentityProviderUnavailableError
    return {str(name): value for name, value in document.items()}


def text_of(document: Mapping[str, object], name: str) -> str:
    value = document.get(name)
    if not isinstance(value, str):
        raise IdentityProviderUnavailableError
    return value
