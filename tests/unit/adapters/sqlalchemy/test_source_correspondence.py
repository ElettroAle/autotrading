"""ADR migrazione-delle-fonti-al-modello-ad-adapter: the sources of the flows before the adapters, each a source with
one of its adapters, weights and parameters unchanged.
"""

import pytest

from autotrading.adapters.outbound.sqlalchemy.source_correspondence import (
    MIGRATION_MARKER,
    document_in_adapters,
    is_before_the_adapters,
    migrated_document,
    sample_reader_of,
)

OLD_SENTIMENTS = [
    {"name": "sentiment-alternative-me", "weight": 4, "parameters": {}},
    {"name": "indicatori", "weight": 2, "parameters": {"lunghezza_serie": 20}},
    {"name": "sentiment-coinmarketcap", "weight": 6, "parameters": {}},
]


def test_the_two_sentiments_become_one_source_with_two_adapters_in_their_order() -> None:
    document = document_in_adapters({"assets": ["BTC"], "sources": OLD_SENTIMENTS})

    assert document == {
        "assets": ["BTC"],
        "sources": [
            {
                "name": "sentiment",
                "adapters": [
                    {"name": "alternative.me", "weight": 4, "parameters": {}},
                    {"name": "CoinMarketCap", "weight": 6, "parameters": {}},
                ],
            },
            {
                "name": "indicatori",
                "adapters": [{"name": "Hyperliquid", "weight": 2, "parameters": {"lunghezza_serie": 20}}],
            },
        ],
    }


@pytest.mark.parametrize(
    ("old", "source", "adapter"),
    [
        ("indicatori", "indicatori", "Hyperliquid"),
        ("pivot", "pivot", "Hyperliquid"),
        ("forecast", "forecast", "Prophet"),
        ("notizie", "notizie", "RSS"),
        ("sentiment-alternative-me", "sentiment", "alternative.me"),
        ("sentiment-coinmarketcap", "sentiment", "CoinMarketCap"),
    ],
)
def test_every_source_before_the_adapters_has_its_source_and_adapter(old: str, source: str, adapter: str) -> None:
    converted = document_in_adapters({"sources": [{"name": old, "weight": 3, "parameters": {"p": 1}}]})

    assert converted["sources"] == [
        {"name": source, "adapters": [{"name": adapter, "weight": 3, "parameters": {"p": 1}}]}
    ]


def test_a_source_the_platform_never_had_keeps_its_name_as_adapter_and_is_refused_when_used() -> None:
    converted = document_in_adapters({"sources": [{"name": "oroscopo", "weight": 5, "parameters": {}}]})

    assert converted["sources"] == [
        {"name": "oroscopo", "adapters": [{"name": "oroscopo", "weight": 5, "parameters": {}}]}
    ]


def test_a_document_is_before_the_adapters_when_a_source_has_no_adapters() -> None:
    assert is_before_the_adapters({"sources": OLD_SENTIMENTS})
    assert not is_before_the_adapters(document_in_adapters({"sources": OLD_SENTIMENTS}))
    assert not is_before_the_adapters({"sources": []})


def test_a_document_already_in_adapters_is_unchanged() -> None:
    document = document_in_adapters({"sources": OLD_SENTIMENTS})

    assert document_in_adapters(document) == document


def test_the_last_version_before_the_adapters_gets_a_new_document_with_the_marker() -> None:
    old = {"sources": OLD_SENTIMENTS, "instructions": "prudente"}

    assert migrated_document(old) == {**document_in_adapters(old), "migrated_from": "sources-v1"}
    assert MIGRATION_MARKER == ("migrated_from", "sources-v1")


def test_a_last_version_already_in_adapters_gets_no_new_version() -> None:
    assert migrated_document(document_in_adapters({"sources": OLD_SENTIMENTS})) is None


@pytest.mark.parametrize(
    ("old", "reader"),
    [
        ("sentiment-alternative-me", ("sentiment", "alternative.me")),
        ("sentiment-coinmarketcap", ("sentiment", "CoinMarketCap")),
        ("notizie", ("notizie", "RSS")),
    ],
)
def test_a_value_collected_before_the_adapters_gets_its_source_and_adapter(old: str, reader: tuple[str, str]) -> None:
    assert sample_reader_of(old) == reader
