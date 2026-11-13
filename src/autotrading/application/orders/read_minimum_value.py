from decimal import Decimal

from autotrading.application.orders.order_failures import FailureNames, answered_or_named
from autotrading.application.orders.ports import VerificationAssetPort
from autotrading.application.orders.read_market import ReadMarketCommand, ReadMarketUseCase


class ReadMinimumValueUseCase:
    """The smallest value of an order the exchange of the account accepts on the asset, read now (R0.4.1).

    The procedure of verification chooses the value of its opening by it; its failures carry the names the procedure
    gave them (ADR 0086).
    """

    def __init__(self, market: ReadMarketUseCase, failures: FailureNames) -> None:
        self._market = market
        self._failures = failures

    def execute(self, asset: VerificationAssetPort) -> Decimal:
        command = ReadMarketCommand(asset.account_id, asset.coin)
        market = answered_or_named(
            lambda: self._market.execute(command), self._failures.account_missing, self._failures.failed
        )
        return market.min_order_value
