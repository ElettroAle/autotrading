from decimal import Decimal

from autotrading.domain.sources.volume_figures import VolumeFigures, unlisted_note, volume_weighted

VALUES = {
    "volume_24h_usd": "1500000000",
    "rapporto_taker_buy_sell": "1.5000",
    "squilibrio_order_book_1_percento": "0.6227",
}


def test_the_values_round_the_volume_to_the_dollar_and_the_ratios_to_four_decimals() -> None:
    figures = VolumeFigures(Decimal("1500000000.4"), Decimal("1.5"), Decimal("0.622653"))

    assert figures.values() == VALUES


def test_a_ratio_not_known_is_not_among_the_values() -> None:
    assert VolumeFigures(Decimal(10), None, None).values() == {"volume_24h_usd": "10"}


def test_the_values_read_back_as_the_figures() -> None:
    assert VolumeFigures.of_values(VALUES) == VolumeFigures(Decimal(1500000000), Decimal("1.5"), Decimal("0.6227"))
    assert VolumeFigures.of_values({"volume_24h_usd": "10"}) == VolumeFigures(Decimal(10), None, None)


def test_a_note_has_no_figures() -> None:
    assert VolumeFigures.of_values(unlisted_note("Borsa")) is None


def test_an_asset_not_listed_is_declared_with_the_adapter() -> None:
    assert unlisted_note("Borsa") == {"nota": "non quotato su Borsa"}


def test_the_aggregate_sums_the_volumes_and_weighs_the_ratios_on_them() -> None:
    large = VolumeFigures(Decimal(300), Decimal(2), Decimal("0.6"))
    small = VolumeFigures(Decimal(100), Decimal(1), Decimal("0.2"))

    assert volume_weighted((large, small)) == VolumeFigures(Decimal(400), Decimal("1.75"), Decimal("0.5"))


def test_a_ratio_not_known_stays_out_of_its_aggregate() -> None:
    known = VolumeFigures(Decimal(300), Decimal(2), None)
    unknown = VolumeFigures(Decimal(100), None, None)

    assert volume_weighted((known, unknown)) == VolumeFigures(Decimal(400), Decimal(2), None)


def test_without_volume_the_ratios_have_no_aggregate() -> None:
    idle = VolumeFigures(Decimal(0), Decimal(2), Decimal("0.5"))

    assert volume_weighted((idle, idle)) == VolumeFigures(Decimal(0), None, None)
