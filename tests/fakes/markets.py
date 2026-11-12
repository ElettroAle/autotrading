"""Fake of the markets of an exchange: the assets it trades now."""

from autotrading.application.flows.errors import FlowExchangeUnavailableError

TRADABLE_ASSETS = frozenset({"BTC", "ETH", "SOL"})


class FakeMarketsAdapter:
    """An exchange that trades the assets it was told to, and may be out of reach."""

    def __init__(self, assets: frozenset[str] = TRADABLE_ASSETS) -> None:
        self.assets = assets
        self.reachable = True

    def tradable_assets(self) -> frozenset[str]:
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.assets
