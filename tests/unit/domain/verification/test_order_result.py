from decimal import Decimal

from autotrading.domain.verification.order_result import OrderResult


def test_an_executed_order_succeeds_with_its_fee_and_realized_result() -> None:
    result = OrderResult.reported(Decimal("0.005"), Decimal("1.75"), None, "eseguito")

    assert result == OrderResult(succeeded=True, fee=Decimal("0.005"), realized_pnl=Decimal("1.75"))


def test_a_refused_order_fails_with_the_message_of_the_exchange() -> None:
    result = OrderResult.reported(None, None, "Insufficient margin", "rifiutato")

    assert result == OrderResult(succeeded=False, message="Insufficient margin")


def test_an_order_without_outcome_fails_with_its_status() -> None:
    assert OrderResult.reported(None, None, None, "senza esito") == OrderResult(succeeded=False, message="senza esito")


def test_an_execution_without_realized_result_is_not_a_success() -> None:
    assert not OrderResult.reported(Decimal("0.005"), None, None, "senza esito").succeeded
