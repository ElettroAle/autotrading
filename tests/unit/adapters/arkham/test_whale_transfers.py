"""The Arkham adapter of the large transfers against answers served in memory (ADR fonte-whale-con-adapter-arkham)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from autotrading.adapters.outbound.arkham.whale_transfers import (
    API_KEY,
    ARKHAM_URL,
    DECLARATION,
    ArkhamWhaleTransfersAdapter,
)
from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.whale import MINIMUM_USD
from autotrading.domain.sources.whale_transfer import WhaleTransfer

UNTIL = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SINCE = UNTIL - timedelta(hours=1)
KEY = {API_KEY.name: "K-ARKHAM"}
REFUSED = "connection refused"


def address(entity: str | None = None, label: str | None = None) -> dict[str, object]:
    described: dict[str, object] = {"address": "0xabc", "chain": "ethereum"}
    if entity is not None:
        described["arkhamEntity"] = {"id": entity.lower(), "name": entity, "type": "cex"}
    if label is not None:
        described["arkhamLabel"] = {"address": "0xabc", "name": label}
    return described


def transfer(origin: dict[str, object], destination: dict[str, object], **changes: object) -> dict[str, object]:
    document: dict[str, object] = {
        "blockTimestamp": "2026-11-20T09:40:00Z",
        "fromAddress": origin,
        "toAddress": destination,
        "tokenSymbol": "BTC",
        "unitValue": 500.0,
        "historicalUSD": 45000000.5,
    }
    return {**document, **changes}


def answering(status: int, document: object, requests: list[httpx.Request] | None = None) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        return httpx.Response(status, json=document)

    return httpx.MockTransport(handle)


def adapter(transport: httpx.MockTransport) -> ArkhamWhaleTransfersAdapter:
    return ArkhamWhaleTransfersAdapter(httpx.Client(transport=transport, base_url=ARKHAM_URL))


def read(transport: httpx.MockTransport, credentials: dict[str, str] = KEY) -> list[WhaleTransfer]:
    return list(adapter(transport).transfers(SINCE, UNTIL, 1_000_000, credentials))


def test_declares_the_secret_key_its_threshold_and_its_history() -> None:
    [threshold] = DECLARATION.parameters

    assert (DECLARATION.name, DECLARATION.offers_history, DECLARATION.configuration_fields) == (
        "Arkham",
        True,
        (API_KEY,),
    )
    assert API_KEY.secret
    assert (threshold.key, threshold.default, threshold.minimum, threshold.maximum) == (
        MINIMUM_USD,
        1_000_000,
        100_000,
        1_000_000_000,
    )
    assert ArkhamWhaleTransfersAdapter(httpx.Client()).declaration() is DECLARATION


def test_asks_the_transfers_of_the_window_above_the_threshold_with_the_key() -> None:
    requests: list[httpx.Request] = []

    read(answering(200, {"count": 0, "transfers": []}, requests))

    [request] = requests
    assert (request.method, request.url.path, request.headers["API-Key"]) == ("GET", "/transfers", "K-ARKHAM")
    assert dict(request.url.params) == {
        "timeGte": str(int(SINCE.timestamp() * 1000)),
        "timeLte": str(int(UNTIL.timestamp() * 1000)),
        "usdGte": "1000000",
        "sortKey": "usd",
        "sortDir": "desc",
        "limit": "100",
    }


def test_every_transfer_keeps_instant_asset_quantity_value_and_the_described_ends() -> None:
    document = {"transfers": [transfer(address(label="Whale 7"), address("Binance", "Hot Wallet"))]}

    assert read(answering(200, document)) == [
        WhaleTransfer(
            datetime(2026, 11, 20, 9, 40, tzinfo=UTC),
            "BTC",
            Decimal("500.0"),
            Decimal("45000000.5"),
            "Whale 7",
            "Binance (Hot Wallet)",
        )
    ]


@pytest.mark.parametrize(
    ("described", "expected"),
    [
        (address("Binance"), "Binance"),
        (address(label="Binance Deposit"), "Binance Deposit"),
        (address(), None),
        ({**address(), "arkhamEntity": None, "arkhamLabel": None}, None),
    ],
)
def test_an_end_is_described_by_its_entity_and_label_when_known(described: dict[str, object], expected: str) -> None:
    [moved] = read(answering(200, {"transfers": [transfer(described, address())]}))

    assert moved.origin == expected


def test_without_transfers_in_the_window_answers_none() -> None:
    assert read(answering(200, {"count": 0})) == []


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_key_is_a_refusal_of_the_credentials_and_permanent(status: int) -> None:
    with pytest.raises(SourceCredentialsRejectedError) as raised:
        read(answering(status, {"message": "Could not verify API Key"}))

    assert (str(raised.value), raised.value.permanent) == ("credenziali rifiutate dal fornitore: Arkham", True)


@pytest.mark.parametrize(("status", "permanent"), [(429, False), (500, False), (400, False)])
def test_any_other_error_status_leaves_the_source_unavailable(status: int, permanent: bool) -> None:
    with pytest.raises(SourceUnavailableError) as raised:
        read(answering(status, {"message": "error"}))

    assert (str(raised.value), raised.value.permanent) == ("fonte non raggiungibile: Arkham", permanent)


def test_a_provider_out_of_reach_leaves_the_source_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    with pytest.raises(SourceUnavailableError, match=r"^fonte non raggiungibile: Arkham$"):
        read(httpx.MockTransport(refuse))


def test_an_answer_that_is_not_json_leaves_the_source_unavailable() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text="<html>"))

    with pytest.raises(SourceUnavailableError):
        read(transport)


@pytest.mark.parametrize(
    "change",
    [
        lambda moved: moved.pop("tokenSymbol"),
        lambda moved: moved.update(historicalUSD=None),
        lambda moved: moved.update(unitValue=0),
        lambda moved: moved.update(blockTimestamp="ieri"),
        lambda moved: moved.update(fromAddress="0xabc"),
    ],
)
def test_a_transfer_of_an_unexpected_shape_leaves_the_source_unavailable(
    change: Callable[[dict[str, object]], object],
) -> None:
    moved = transfer(address(), address())
    change(moved)

    with pytest.raises(SourceUnavailableError):
        read(answering(200, {"transfers": [moved]}))


def test_a_document_of_an_unexpected_shape_leaves_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        read(answering(200, ["not", "a", "document"]))


def test_credentials_without_the_key_are_refused_by_the_provider() -> None:
    requests: list[httpx.Request] = []

    with pytest.raises(SourceCredentialsRejectedError):
        read(answering(401, {"message": "Could not verify API Key"}, requests), credentials={})

    assert requests[0].headers["API-Key"] == ""
