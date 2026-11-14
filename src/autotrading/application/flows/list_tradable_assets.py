from collections.abc import Mapping

from autotrading.application.flows.ports import MarketsPort


class ListTradableAssetsUseCase:
    """The assets a flow can trade now on the exchanges of the installation, by name, each once (R1.1.1, ADR 0147)."""

    def __init__(self, markets: Mapping[str, MarketsPort]) -> None:
        self._markets = markets

    def execute(self) -> tuple[str, ...]:
        tradable = frozenset[str]().union(*(market.tradable_assets() for market in self._markets.values()))
        return tuple(sorted(tradable))
