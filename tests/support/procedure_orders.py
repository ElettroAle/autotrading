"""The orders of the procedure of verification, as the worker composes them (ADR 0024, ADR 0086)."""

from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.close_verification_position import CloseVerificationPositionUseCase
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.orders.open_verification_position import OpenVerificationPositionUseCase
from autotrading.application.orders.order_failures import FailureNames
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.orders.read_minimum_value import ReadMinimumValueUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.application.verification.ports import ProcedureOrders

VERIFICATION_FAILURES = FailureNames(VerificationAccountNotFoundError, VerificationStepError)


def procedure_orders(
    opening: OpenPositionUseCase, closing: CloseExchangePositionUseCase, market: ReadMarketUseCase
) -> ProcedureOrders:
    return ProcedureOrders(
        ReadMinimumValueUseCase(market, VERIFICATION_FAILURES),
        OpenVerificationPositionUseCase(opening, VERIFICATION_FAILURES),
        CloseVerificationPositionUseCase(closing, VERIFICATION_FAILURES),
    )
