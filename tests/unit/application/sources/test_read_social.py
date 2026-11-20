from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import (
    AssetRequiredError,
    SourceCredentialsRejectedError,
    SourceUnavailableError,
)
from autotrading.application.sources.ports import SourceRequest
from autotrading.application.sources.read_social import ReadSocialUseCase
from autotrading.domain.sources.social import POSTS
from autotrading.domain.sources.social_snapshot import SocialPost, SocialSnapshot
from autotrading.domain.sources.source_sample import SourceValue
from tests.fakes.social import API_KEY, FakeSocialAdapter, SocialAsked

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
KEY = {API_KEY.name: "K-LUNAR"}
FIRST = SocialPost("satoshi", NOW - timedelta(hours=1), "il prezzo sale")
SECOND = SocialPost("vitalik", NOW - timedelta(hours=2), "il prezzo scende")
THIRD = SocialPost("anatoly", NOW - timedelta(hours=3), "il prezzo resta")
SNAPSHOT = SocialSnapshot(64, 1200, 98000, (FIRST, SECOND, THIRD))


def request(asset: str | None = "BTC", posts: int = 2) -> SourceRequest:
    return SourceRequest(uuid4(), asset, {POSTS: posts}, NOW, KEY)


def test_asks_the_provider_for_the_asset_and_the_number_of_posts_with_the_credentials_of_the_tenant() -> None:
    provider = FakeSocialAdapter("Social", published={"BTC": SNAPSHOT})

    ReadSocialUseCase(provider).execute(request())

    assert provider.asked == [SocialAsked("BTC", 2, KEY)]


def test_the_figures_refer_to_the_reading_and_every_post_kept_to_its_own_instant() -> None:
    provider = FakeSocialAdapter("Social", published={"BTC": SNAPSHOT})

    values = ReadSocialUseCase(provider).execute(request())

    assert values == (
        SourceValue(NOW, {"sentiment_percento": "64", "menzioni_24h": "1200", "interazioni_24h": "98000"}),
        SourceValue(FIRST.at, FIRST.values()),
        SourceValue(SECOND.at, SECOND.values()),
    )


def test_a_per_asset_source_asked_without_an_asset_is_a_defect() -> None:
    with pytest.raises(AssetRequiredError):
        ReadSocialUseCase(FakeSocialAdapter("Social")).execute(request(asset=None))


@pytest.mark.parametrize(
    ("reachable", "rejects_credentials", "error"),
    [(False, False, SourceUnavailableError), (True, True, SourceCredentialsRejectedError)],
)
def test_the_errors_of_the_provider_reach_the_cycle(
    reachable: bool, rejects_credentials: bool, error: type[Exception]
) -> None:
    provider = FakeSocialAdapter(
        "Social", published={"BTC": SNAPSHOT}, reachable=reachable, rejects_credentials=rejects_credentials
    )

    with pytest.raises(error):
        ReadSocialUseCase(provider).execute(request())
