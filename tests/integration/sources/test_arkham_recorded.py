"""The Arkham adapter of the large transfers against the answers of the Intel API recorded from its official
documentation, without a key and without spending (ADR risposte-http-registrate-per-i-fornitori-a-chiave).

- Success: the example of GET /transfers, https://intel.arkm.com/llms/get-transfers.md
- 401 and 403: the common errors, https://intel.arkm.com/llms/guides/errors-http-codes.md
- 429 and 500: the error format of the same page, `{ "message": "description" }`

A test with the real key, outside the suite, joins these when the owner gives one.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from autotrading.adapters.outbound.arkham.whale_transfers import API_KEY, ARKHAM_URL, ArkhamWhaleTransfersAdapter
from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.whale_transfer import WhaleTransfer

pytestmark = pytest.mark.integration

RECORDED = Path(__file__).parent / "recorded" / "arkham"
UNTIL = datetime(2026, 7, 9, 16, 0, tzinfo=UTC)
SINCE = UNTIL - timedelta(hours=1)
THRESHOLD = 1_000_000
KEY = "K-RECORDED"


def recorded(name: str) -> object:
    document: object = json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))
    return document


class RecordedArkham:
    """Answers every request with one recorded answer and keeps the requests it received."""

    def __init__(self, name: str, status: int = 200) -> None:
        self._document = recorded(name)
        self._status = status
        self.requests: list[httpx.Request] = []

    def adapter(self) -> ArkhamWhaleTransfersAdapter:
        transport = httpx.MockTransport(self._answer)
        return ArkhamWhaleTransfersAdapter(httpx.Client(transport=transport, base_url=ARKHAM_URL))

    def read(self) -> list[WhaleTransfer]:
        return list(self.adapter().transfers(SINCE, UNTIL, THRESHOLD, {API_KEY.name: KEY}))

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self._status, json=self._document)


def test_the_documented_transfers_become_the_large_transfers_with_their_described_ends() -> None:
    arkham = RecordedArkham("transfers")

    assert arkham.read() == [
        WhaleTransfer(
            datetime(2026, 7, 9, 15, 16, 47, tzinfo=UTC),
            "USDC",
            Decimal("2995710.06"),
            Decimal("2995710.06"),
            "Binance (Hot Wallet)",
            None,
        ),
        WhaleTransfer(
            datetime(2026, 7, 9, 15, 13, 10, tzinfo=UTC),
            "USDC",
            Decimal("1637110.638546851"),
            Decimal("1637110.638546851"),
            "Binance Deposit",
            "Binance (Hot Wallet)",
        ),
    ]


def test_the_request_asks_the_transfers_of_the_window_above_the_threshold_with_the_key_header() -> None:
    arkham = RecordedArkham("transfers")

    arkham.read()

    [request] = arkham.requests
    assert str(request.url).split("?")[0] == "https://api.arkm.com/transfers"
    assert request.headers["API-Key"] == KEY
    assert "Authorization" not in request.headers
    assert dict(request.url.params) == {
        "timeGte": "1783609200000",
        "timeLte": "1783612800000",
        "usdGte": "1000000",
        "sortKey": "usd",
        "sortDir": "desc",
        "limit": "100",
    }


@pytest.mark.parametrize(("name", "status"), [("unauthorized_401", 401), ("forbidden_403", 403)])
def test_a_refused_key_is_a_permanent_refusal_of_the_credentials(name: str, status: int) -> None:
    with pytest.raises(SourceCredentialsRejectedError) as raised:
        RecordedArkham(name, status).read()

    assert (str(raised.value), raised.value.permanent) == ("credenziali rifiutate dal fornitore: Arkham", True)


@pytest.mark.parametrize(("name", "status"), [("rate_limited_429", 429), ("server_error_500", 500)])
def test_a_rate_limit_or_a_server_error_is_a_transient_unavailability(name: str, status: int) -> None:
    with pytest.raises(SourceUnavailableError) as raised:
        RecordedArkham(name, status).read()

    assert (str(raised.value), raised.value.permanent) == ("fonte non raggiungibile: Arkham", False)
