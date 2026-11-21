"""ADR-fonti-provate-su-risposte-registrate: the integration tests of the sources run on real answers of the services,
captured once live and saved as they arrived, each with the recording that says which request received it, from which
URL and when; no test of a source calls a service live, and every source has a recorded error (Bug 699).
"""

import ast
import json
import re
from pathlib import Path

import pytest
from hyperliquid.utils.constants import TESTNET_API_URL

from tests.support.recorded_answers import (
    RECORDED,
    RECORDING_SUFFIX,
    RecordedHttpxService,
    RecordedInfoSdk,
    RecordedService,
)

INTEGRATION = RECORDED.parent
# The technologies of the sources whose tests used to call the services live.
FORMERLY_LIVE = ("alternative_me", "binance", "coinmarketcap", "hyperliquid", "rss")
RECORDING_FIELDS = frozenset({"origin", "recorded_at", "method", "url", "request_body", "status", "answer"})
# What answers a test off the network: the transport of httpx that never opens a connection, or the recorded services.
OFF_THE_NETWORK = frozenset({"MockTransport", "RecordedHttpxService", "RecordedInfoSdk"})
# What reaches a service: the clients of the composition and of the networks, a client of httpx without a transport.
LIVE_BUILDERS = frozenset({"for_network", "get", "post", "stream"})


def _name_of(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def live_call_flaws(test_name: str, test_source: str) -> list[str]:
    """What makes a test module of the sources reach a service: an empty list when it runs on recorded answers."""
    tree = ast.parse(test_source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    names = {_name_of(call) for call in calls} | {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    flaws = []
    if not test_name.endswith("_recorded.py"):
        flaws.append(f"{test_name} is not a test on recorded answers (test_<source>_recorded.py)")
    if "integration" not in attributes:
        flaws.append(f"{test_name} without the marker integration")
    if not OFF_THE_NETWORK & (names | attributes):
        flaws.append(f"{test_name} answered by no recording")
    flaws.extend(
        f"{test_name} reaches the service: {ast.unparse(call)}"
        for call in calls
        if _name_of(call) in LIVE_BUILDERS
        or _name_of(call).endswith("_adapters")
        or (_name_of(call) == "Client" and "transport" not in {keyword.arg for keyword in call.keywords})
    )
    return flaws


def recording_flaws(folder: Path) -> list[str]:
    """What the recorded answers of a technology miss of the decision: an empty list when they follow it."""
    recordings = sorted(folder.glob(f"*{RECORDING_SUFFIX}"))
    answers = {path.name for path in folder.iterdir() if not path.name.endswith(RECORDING_SUFFIX)}
    flaws = [f"{folder.name} has no recorded answer"] if not recordings else []
    statuses = []
    for path in recordings:
        recording = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(RECORDING_FIELDS - set(recording))
        if missing:
            flaws.append(f"{path.name} without {', '.join(missing)}")
            continue
        if not str(recording["url"]).startswith("https://"):
            flaws.append(f"{path.name} without the URL it was recorded from")
        if recording["answer"] not in answers:
            flaws.append(f"{path.name} without its answer {recording['answer']}")
        statuses.append(int(recording["status"]))
    described = {path.name.removesuffix(RECORDING_SUFFIX) for path in recordings}
    flaws.extend(
        f"{answer} without its recording" for answer in sorted(answers) if answer.split(".")[0] not in described
    )
    if not any(status == 429 or status >= 500 for status in statuses):
        flaws.append(f"{folder.name} without a recorded error 429 or 5xx")
    return flaws


CONFORMING_TEST = """
import pytest
pytestmark = pytest.mark.integration
def test_index():
    service = RecordedHttpxService("coinmarketcap", "fear_and_greed_latest")
    CoinMarketCapSentimentAdapter(service.client()).read_index({})
"""
LIVE_TEST = """
def test_index():
    with httpx.Client() as client:
        CoinMarketCapSentimentAdapter(client).read_index({})
    HyperliquidMarketDataAdapter.for_network(testnet=True).snapshot("BTC")
    binance_adapters().snapshot("BTC", 15)
"""


@pytest.mark.parametrize(
    ("name", "source", "flaws"),
    [
        ("test_sentiment_recorded.py", CONFORMING_TEST, []),
        (
            "test_sentiment_live.py",
            LIVE_TEST,
            [
                "test_sentiment_live.py is not a test on recorded answers (test_<source>_recorded.py)",
                "test_sentiment_live.py without the marker integration",
                "test_sentiment_live.py answered by no recording",
                "test_sentiment_live.py reaches the service: httpx.Client()",
                "test_sentiment_live.py reaches the service: HyperliquidMarketDataAdapter.for_network(testnet=True)",
                "test_sentiment_live.py reaches the service: binance_adapters()",
            ],
        ),
    ],
)
def test_adr_fonti_provate_su_risposte_registrate_a_live_test_of_a_source_is_found(
    name: str, source: str, flaws: list[str]
) -> None:
    assert sorted(live_call_flaws(name, source)) == sorted(flaws)


def _recordings(folder: Path, recordings: dict[str, dict[str, object]], answers: tuple[str, ...]) -> Path:
    folder.mkdir()
    for name, recording in recordings.items():
        (folder / f"{name}{RECORDING_SUFFIX}").write_text(json.dumps(recording), encoding="utf-8")
    for answer in answers:
        (folder / answer).write_text("{}", encoding="utf-8")
    return folder


def _recording(answer: str, status: int, url: str = "https://api.example/fng") -> dict[str, object]:
    return {
        "origin": "live",
        "recorded_at": "2026-11-21T20:09:09Z",
        "method": "GET",
        "url": url,
        "request_body": None,
        "status": status,
        "answer": answer,
    }


def test_adr_fonti_provate_su_risposte_registrate_recordings_with_their_request_and_an_error_follow_it(
    tmp_path: Path,
) -> None:
    recordings = {"index": _recording("index.json", 200), "rate_limited_429": _recording("rate_limited_429.txt", 429)}

    assert recording_flaws(_recordings(tmp_path / "source", recordings, ("index.json", "rate_limited_429.txt"))) == []


def test_adr_fonti_provate_su_risposte_registrate_answers_without_recording_url_or_error_are_found(
    tmp_path: Path,
) -> None:
    recordings: dict[str, dict[str, object]] = {
        "index": _recording("index.json", 200, "api.example/fng"),
        "book": {"answer": "book.json"},
    }

    folder = _recordings(tmp_path / "source", recordings, ("index.json", "candles.json"))

    assert recording_flaws(folder) == [
        "book.recording.json without method, origin, recorded_at, request_body, status, url",
        "index.recording.json without the URL it was recorded from",
        "candles.json without its recording",
        "source without a recorded error 429 or 5xx",
    ]


@pytest.mark.parametrize("test_module", sorted(INTEGRATION.glob("test_*.py")), ids=lambda path: path.name)
def test_adr_fonti_provate_su_risposte_registrate_no_test_of_a_source_calls_a_service_live(test_module: Path) -> None:
    assert live_call_flaws(test_module.name, test_module.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("technology", FORMERLY_LIVE)
def test_adr_fonti_provate_su_risposte_registrate_every_answer_has_its_recording_and_an_error(technology: str) -> None:
    assert recording_flaws(RECORDED / technology) == []


def test_adr_fonti_provate_su_risposte_registrate_an_unrecorded_request_fails_instead_of_reaching_the_network() -> None:
    client = RecordedHttpxService("coinmarketcap", "fear_and_greed_latest").client()

    with pytest.raises(
        pytest.fail.Exception, match=re.escape("no recorded answer for GET https://api.alternative.me/fng/")
    ):
        client.get("https://api.alternative.me/fng/")


def test_adr_fonti_provate_su_risposte_registrate_the_sdk_asks_only_the_recorded_info_endpoint() -> None:
    sdk = RecordedInfoSdk(RecordedService("hyperliquid", "meta"))

    with pytest.raises(
        pytest.fail.Exception, match=re.escape("no recorded answer for POST https://api.hyperliquid.xyz/info")
    ):
        sdk.info(TESTNET_API_URL, 3.0).session.post("https://api.hyperliquid.xyz/info", json={"type": "allMids"})
