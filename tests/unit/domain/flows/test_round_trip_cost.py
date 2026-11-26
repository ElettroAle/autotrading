from decimal import Decimal

from autotrading.domain.flows.round_trip_cost import RoundTripCost


def test_the_cost_counts_the_fee_of_the_opening_and_of_the_closing_in_percent() -> None:
    assert RoundTripCost.of_rate(Decimal("0.00045")).percent == Decimal("0.09")


def test_the_percent_keeps_no_trailing_zeros_and_no_exponent() -> None:
    assert str(RoundTripCost.of_rate(Decimal("0.00045")).percent) == "0.09"
    assert str(RoundTripCost.of_rate(Decimal("0.05")).percent) == "10"
    assert str(RoundTripCost.of_rate(Decimal(0)).percent) == "0"


def test_a_cost_read_is_no_missing_datum() -> None:
    assert RoundTripCost.of_rate(Decimal("0.00045")).missing == ()


def test_a_fee_not_read_is_a_missing_datum_with_its_reason_and_no_cost() -> None:
    unread = RoundTripCost.unread("exchange non raggiungibile, riprovare")

    assert unread.missing == ("costo di andata e ritorno: exchange non raggiungibile, riprovare",)
    assert unread.percent is None


def test_with_the_option_off_nothing_is_read_and_nothing_is_missing() -> None:
    assert (RoundTripCost().percent, RoundTripCost().missing) == (None, ())
