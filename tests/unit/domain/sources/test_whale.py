from autotrading.domain.sources.whale import WHALE, no_large_transfers


def test_no_large_transfer_is_a_datum_not_an_absent_source() -> None:
    assert no_large_transfers({}) == {"nota": "nessun grande trasferimento nell'ultimo intervallo"}


def test_the_whale_source_is_a_market_source_that_tells_its_silence() -> None:
    assert WHALE.name == "whale"
    assert not WHALE.per_asset
    assert WHALE.silence_note(WHALE.settings({})) == {"nota": "nessun grande trasferimento nell'ultimo intervallo"}
