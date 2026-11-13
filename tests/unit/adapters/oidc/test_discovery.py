import io
import json
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from autotrading.adapters.outbound.oidc.discovery import discovery_url_of, fetch_json, text_of
from autotrading.application.tenancy.errors import IdentityProviderUnavailableError

URL = "https://login.example.test/.well-known/openid-configuration"


@contextmanager
def serving(body: bytes) -> Iterator[None]:
    with patch("urllib.request.urlopen", return_value=io.BytesIO(body)):
        yield


def test_the_discovery_url_follows_the_issuer_without_doubling_the_slash() -> None:
    assert discovery_url_of("https://idp.test/t/v2.0/") == "https://idp.test/t/v2.0/.well-known/openid-configuration"


def test_the_directory_is_reached_only_over_https() -> None:
    with pytest.raises(IdentityProviderUnavailableError):
        fetch_json("http://login.example.test/.well-known/openid-configuration")


def test_a_json_object_is_read_as_a_document() -> None:
    with serving(json.dumps({"jwks_uri": "https://idp.test/keys"}).encode()):
        assert fetch_json(URL) == {"jwks_uri": "https://idp.test/keys"}


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]"], ids=["not-json", "not-an-object"])
def test_an_answer_that_is_not_a_json_object_is_unavailable(body: bytes) -> None:
    with serving(body), pytest.raises(IdentityProviderUnavailableError):
        fetch_json(URL)


@pytest.mark.parametrize("document", [{}, {"name": 7}], ids=["absent", "not-text"])
def test_a_text_field_that_is_absent_or_not_text_is_unavailable(document: dict[str, object]) -> None:
    with pytest.raises(IdentityProviderUnavailableError):
        text_of(document, "name")
