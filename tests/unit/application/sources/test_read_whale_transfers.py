from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.application.sources.ports import SourceRequest
from autotrading.application.sources.read_whale_transfers import ReadWhaleTransfersUseCase
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.whale import MINIMUM_USD
from autotrading.domain.sources.whale_transfer import WhaleTransfer
from tests.fakes.whale_transfers import FakeWhaleTransfersAdapter, TransfersAsked

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
KEY = {"api_key": "K-WHALE"}


def request(threshold: int = 1_000_000) -> SourceRequest:
    return SourceRequest(uuid4(), None, {MINIMUM_USD: threshold}, NOW, KEY)


def test_asks_the_provider_for_the_last_interval_of_the_flow_at_the_threshold_with_the_credentials() -> None:
    provider = FakeWhaleTransfersAdapter("Balene")

    ReadWhaleTransfersUseCase(provider, 60).execute(request(2_500_000))

    assert provider.asked == [TransfersAsked(NOW - timedelta(minutes=60), NOW, 2_500_000, KEY)]


def test_every_large_transfer_is_a_value_referring_to_its_instant_newest_first() -> None:
    older = WhaleTransfer(NOW - timedelta(minutes=50), "ETH", Decimal("1200.50"), Decimal("4100000.25"), "Kraken", None)
    newer = WhaleTransfer(NOW - timedelta(minutes=5), "BTC", Decimal("500.0"), Decimal("45000000"), None, "Binance")
    provider = FakeWhaleTransfersAdapter("Balene", published=[older, newer])

    values = ReadWhaleTransfersUseCase(provider, 60).execute(request())

    assert values == (
        SourceValue(
            newer.at,
            {
                "data_ora": "2026-11-20T09:55:00+00:00",
                "asset": "BTC",
                "quantita": "500",
                "controvalore_usd": "45000000",
                "descrizione": "da indirizzo non etichettato a Binance",
            },
        ),
        SourceValue(
            older.at,
            {
                "data_ora": "2026-11-20T09:10:00+00:00",
                "asset": "ETH",
                "quantita": "1200.5",
                "controvalore_usd": "4100000.25",
                "descrizione": "da Kraken a indirizzo non etichettato",
            },
        ),
    )


def test_a_transfer_with_both_ends_unknown_has_no_description() -> None:
    moved = WhaleTransfer(NOW - timedelta(minutes=1), "BTC", Decimal(30), Decimal("2700000"), None, None)

    [value] = ReadWhaleTransfersUseCase(FakeWhaleTransfersAdapter("Balene", published=[moved]), 15).execute(request())

    assert "descrizione" not in value.values


def test_a_transfer_below_the_threshold_the_provider_answered_stays_out() -> None:
    small = WhaleTransfer(NOW - timedelta(minutes=1), "BTC", Decimal(1), Decimal(90000), None, None)
    lenient = FakeWhaleTransfersAdapter("Balene", published=[small], ignores_threshold=True)

    assert ReadWhaleTransfersUseCase(lenient, 60).execute(request()) == ()


def test_no_large_transfer_reads_no_value() -> None:
    assert ReadWhaleTransfersUseCase(FakeWhaleTransfersAdapter("Balene"), 60).execute(request()) == ()


@pytest.mark.parametrize(
    ("provider", "error"),
    [
        (FakeWhaleTransfersAdapter("Balene", reachable=False), SourceUnavailableError),
        (FakeWhaleTransfersAdapter("Balene", rejects_credentials=True), SourceCredentialsRejectedError),
    ],
)
def test_an_error_of_the_provider_reaches_the_cycle(
    provider: FakeWhaleTransfersAdapter, error: type[Exception]
) -> None:
    with pytest.raises(error):
        ReadWhaleTransfersUseCase(provider, 60).execute(request())
