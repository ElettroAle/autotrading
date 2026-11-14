from collections.abc import Mapping

from autotrading.application.accounts.ports import ExchangePort


class ListSupportedExchangesUseCase:
    """The exchanges an account can be registered on, by name: the same ones the registration accepts (R2.3.8,
    ADR 0152)."""

    def __init__(self, exchanges: Mapping[str, ExchangePort]) -> None:
        self._exchanges = exchanges

    def execute(self) -> tuple[str, ...]:
        return tuple(sorted(self._exchanges))
