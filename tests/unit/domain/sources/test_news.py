import pytest

from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS, no_recent_news


@pytest.mark.parametrize(
    ("hours", "note"), [(1, "nessuna notizia nell'ultima ora"), (24, "nessuna notizia nelle ultime 24 ore")]
)
def test_no_recent_news_is_a_datum_within_the_age_of_the_flow(hours: int, note: str) -> None:
    assert no_recent_news({"numero_notizie": 10, "eta_massima_ore": hours}) == {"nota": note}


def test_only_the_news_has_a_meaning_for_its_silence() -> None:
    assert NEWS.silence_note(NEWS.settings({})) == {"nota": "nessuna notizia nelle ultime 24 ore"}
    assert INDICATORS.silence_note(INDICATORS.settings({})) is None
