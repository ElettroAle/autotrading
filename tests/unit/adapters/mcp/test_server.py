"""The server as a client of the tailnet reaches it: health, metadata of the resource, refusals of the tokens."""

import pytest

from tests.support.directory import Person
from tests.support.identity_provider import ISSUER, SCOPE
from tests.support.mcp_session import INITIALIZE, METADATA_URL, PUBLIC_URL, VERSION, McpSession
from tests.support.platform import Platform


@pytest.fixture
def session() -> McpSession:
    return McpSession(Platform())


def test_the_health_names_the_server_and_its_version(session: McpSession) -> None:
    answer = session.get("/health")

    assert (answer.status_code, answer.json()) == (200, {"name": "AutoTrading", "version": VERSION})


def test_the_metadata_of_the_resource_name_the_issuer_and_the_scope_of_the_api(session: McpSession) -> None:
    answer = session.get("/.well-known/oauth-protected-resource/mcp")

    assert answer.status_code == 200
    assert answer.json() == {
        "resource": PUBLIC_URL,
        "authorization_servers": [ISSUER],
        "scopes_supported": [SCOPE],
        "bearer_methods_supported": ["header"],
    }


@pytest.mark.parametrize("authorization", [None, "Bearer not-a-token", "Basic YW5uYTpwdw=="])
def test_a_request_without_a_valid_token_is_refused_toward_the_metadata(
    session: McpSession, authorization: str | None
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}

    answer = session.post("/mcp", INITIALIZE, headers)

    assert answer.status_code == 401
    assert f'resource_metadata="{METADATA_URL}"' in answer.headers["www-authenticate"]


def test_a_person_without_the_role_is_refused_as_the_api_refuses_her(session: McpSession) -> None:
    token = session.identity_provider.token_for(Person("ospite"))

    answer = session.post("/mcp", INITIALIZE, {"Authorization": f"Bearer {token}"})

    assert answer.status_code == 403
    assert answer.json()["error"] == "insufficient_scope"


def test_a_user_opens_a_session_without_state_on_the_server(session: McpSession) -> None:
    answer = session.post("/mcp", INITIALIZE, {"Authorization": f"Bearer {session.token_of('anna')}"})

    assert answer.status_code == 200
    assert answer.headers["content-type"].startswith("application/json")
    assert "mcp-session-id" not in answer.headers
    assert answer.json()["result"]["serverInfo"]["name"] == "AutoTrading"


def test_a_request_for_another_host_is_refused(session: McpSession) -> None:
    headers = {"Authorization": f"Bearer {session.token_of('anna')}", "Host": "attacker.example"}

    answer = session.post("/mcp", INITIALIZE, headers)

    assert answer.status_code == 421
