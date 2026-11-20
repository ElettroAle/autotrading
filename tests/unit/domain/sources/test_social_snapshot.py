from datetime import UTC, datetime, timedelta

import pytest

from autotrading.domain.sources.errors import InvalidSocialSnapshotError
from autotrading.domain.sources.social_snapshot import SocialHour, SocialPost, SocialSnapshot

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)


def post(index: int) -> SocialPost:
    return SocialPost(f"creatore{index}", NOW - timedelta(minutes=index), f"messaggio {index}")


def test_a_post_keeps_author_instant_and_text() -> None:
    written = SocialPost("satoshi", NOW, "il prezzo sale")

    assert (written.author, written.at, written.text) == ("satoshi", NOW, "il prezzo sale")


@pytest.mark.parametrize(
    ("author", "at", "text"),
    [
        (" ", NOW, "testo"),
        ("satoshi", NOW.replace(tzinfo=None), "testo"),
        ("satoshi", NOW, " "),
    ],
)
def test_a_post_without_author_time_zone_or_text_is_refused(author: str, at: datetime, text: str) -> None:
    with pytest.raises(InvalidSocialSnapshotError) as raised:
        SocialPost(author, at, text)

    assert str(raised.value) == "dati social non validi"


def test_a_post_reads_as_author_instant_and_text_for_the_agent() -> None:
    assert post(1).values() == {
        "autore": "creatore1",
        "data_ora": "2026-11-20T09:59:00+00:00",
        "testo": "messaggio 1",
    }


@pytest.mark.parametrize(
    ("sentiment", "mentions", "interactions"),
    [(-1, 0, 0), (101, 0, 0), (50, -1, 0), (50, 0, -1)],
)
def test_a_snapshot_with_a_sentiment_out_of_percent_or_negative_counts_is_refused(
    sentiment: int, mentions: int, interactions: int
) -> None:
    with pytest.raises(InvalidSocialSnapshotError):
        SocialSnapshot(sentiment, mentions, interactions, ())


def test_the_figures_are_the_sentiment_the_mentions_and_the_interactions_of_the_last_24_hours() -> None:
    assert SocialSnapshot(68, 157841, 136486672, ()).values() == {
        "sentiment_percento": "68",
        "menzioni_24h": "157841",
        "interazioni_24h": "136486672",
    }


def test_a_sentiment_nobody_measured_is_left_out_of_the_figures() -> None:
    assert SocialSnapshot(None, 0, 0, ()).values() == {"menzioni_24h": "0", "interazioni_24h": "0"}


def test_the_posts_beyond_the_number_asked_are_discarded_keeping_the_most_relevant() -> None:
    snapshot = SocialSnapshot(50, 1, 1, tuple(post(index) for index in range(1, 8)))

    assert snapshot.most_relevant(5) == tuple(post(index) for index in range(1, 6))
    assert snapshot.most_relevant(20) == snapshot.posts


def test_the_hours_of_a_day_sum_mentions_and_interactions_and_weigh_the_sentiment_on_the_interactions() -> None:
    hours = (SocialHour(80, 10, 3000), SocialHour(40, 5, 1000), SocialHour(0, 0, 0))

    snapshot = SocialSnapshot.of_hours(hours, (post(1),))

    # (80 * 3000 + 40 * 1000) / 4000 = 70.
    assert snapshot == SocialSnapshot(70, 15, 4000, (post(1),))


def test_the_weighted_sentiment_rounds_to_the_closest_percent() -> None:
    snapshot = SocialSnapshot.of_hours((SocialHour(70, 1, 2), SocialHour(71, 1, 1)), ())

    # (140 + 71) / 3 = 70.33.
    assert snapshot.sentiment == 70


def test_hours_without_interactions_have_no_sentiment() -> None:
    assert SocialSnapshot.of_hours((SocialHour(50, 3, 0),), ()) == SocialSnapshot(None, 3, 0, ())
