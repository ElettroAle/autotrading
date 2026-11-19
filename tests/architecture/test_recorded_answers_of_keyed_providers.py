"""ADR-risposte-http-registrate-per-i-fornitori-a-chiave: every adapter of a source that needs a secret key receives an
httpx.Client, and its integration test runs on the answers recorded from the documentation of the provider, citing the
page, checking the request, and recording the errors 401, 429 and 5xx too.
"""

import ast
from pathlib import Path

import pytest

from autotrading.adapters.outbound.arkham import whale_transfers
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration

REPOSITORY = Path(__file__).resolve().parents[2]
INTEGRATION = REPOSITORY / "tests" / "integration" / "sources"
# The adapters of the sources that need a secret key, by the module that declares each of them.
KEYED = {"arkham": whale_transfers}
REQUIRED_ERRORS = ("401", "429", "500")


def needs_a_key(declaration: SourceAdapterDeclaration) -> bool:
    return any(field.secret for field in declaration.configuration_fields)


def recorded_test_flaws(test_source: str, recorded: set[str]) -> list[str]:
    """What the recorded test of an adapter misses of the decision: an empty list when it follows it."""
    tree = ast.parse(test_source)
    texts = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    flaws = []
    if "integration" not in attributes:
        flaws.append("without the marker integration")
    if "MockTransport" not in attributes:
        flaws.append("not on httpx.MockTransport")
    if not any("https://" in text for text in texts):
        flaws.append("without the page of the documentation")
    if "requests" not in attributes:
        flaws.append("without checking the request")
    flaws.extend(
        f"without the recorded error {code}" for code in REQUIRED_ERRORS if not any(code in name for name in recorded)
    )
    return flaws


def constructor_receives_a_client(module_source: str) -> bool:
    """Whether every adapter class of the module receives an httpx.Client in its constructor."""
    classes = [
        node
        for node in ast.parse(module_source).body
        if isinstance(node, ast.ClassDef) and node.name.endswith("Adapter")
    ]
    return bool(classes) and all(
        any(
            isinstance(item, ast.FunctionDef)
            and item.name == "__init__"
            and any(
                ast.unparse(argument.annotation or ast.Constant(None)) == "httpx.Client" for argument in item.args.args
            )
            for item in node.body
        )
        for node in classes
    )


CONFORMING_TEST = """
import httpx
import pytest
pytestmark = pytest.mark.integration
PAGE = "https://provider.example/docs"
def test_request(arkham):
    transport = httpx.MockTransport(answer)
    assert arkham.requests
"""


@pytest.mark.parametrize(
    ("source", "recorded", "flaws"),
    [
        (CONFORMING_TEST, {"transfers", "unauthorized_401", "rate_limited_429", "server_error_500"}, []),
        (
            "def test_live():\n    client = httpx.Client()\n",
            {"transfers"},
            [
                "without the marker integration",
                "not on httpx.MockTransport",
                "without the page of the documentation",
                "without checking the request",
                "without the recorded error 401",
                "without the recorded error 429",
                "without the recorded error 500",
            ],
        ),
    ],
)
def test_adr_risposte_http_registrate_per_i_fornitori_a_chiave_a_test_off_the_recordings_is_found(
    source: str, recorded: set[str], flaws: list[str]
) -> None:
    assert recorded_test_flaws(source, recorded) == flaws


@pytest.mark.parametrize(
    ("source", "receives"),
    [
        ("class KeyedAdapter:\n    def __init__(self, client: httpx.Client) -> None: ...\n", True),
        ("class KeyedAdapter:\n    def __init__(self, url: str) -> None: ...\n", False),
    ],
)
def test_adr_risposte_http_registrate_per_i_fornitori_a_chiave_an_adapter_without_a_client_is_found(
    source: str, receives: bool
) -> None:
    assert constructor_receives_a_client(source) is receives


@pytest.mark.parametrize("adapter", sorted(KEYED))
def test_adr_risposte_http_registrate_per_i_fornitori_a_chiave_every_keyed_adapter_is_proved_on_recordings(
    adapter: str,
) -> None:
    module = KEYED[adapter]
    recorded = {path.stem for path in (INTEGRATION / "recorded" / adapter).glob("*.json")}
    test_source = (INTEGRATION / f"test_{adapter}_recorded.py").read_text(encoding="utf-8")

    assert needs_a_key(module.DECLARATION)
    assert constructor_receives_a_client(Path(str(module.__file__)).read_text(encoding="utf-8"))
    assert recorded_test_flaws(test_source, recorded) == []
