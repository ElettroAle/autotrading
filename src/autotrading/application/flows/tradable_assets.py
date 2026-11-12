from collections.abc import Mapping

from autotrading.application.flows.errors import AssetNotTradableError
from autotrading.application.flows.ports import MarketsPort


def require_tradable(markets: Mapping[str, MarketsPort], exchange: str, assets: tuple[str, ...]) -> None:
    """Every asset is traded now on the exchange of the account (R1.1.1)."""
    market = markets.get(exchange)
    tradable = frozenset() if market is None else market.tradable_assets()
    refused = tuple(asset for asset in assets if asset not in tradable)
    if refused:
        raise AssetNotTradableError(refused)
