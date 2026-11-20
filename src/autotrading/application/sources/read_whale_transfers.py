from datetime import timedelta
from decimal import Decimal

from autotrading.application.sources.ports import SourceRequest, WhaleTransfersPort
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.whale import MINIMUM_USD
from autotrading.domain.sources.whale_transfer import WhaleTransfer, large_transfers


class ReadWhaleTransfersUseCase:
    """Reads the transfers of the last interval of the flow at or above the threshold of the adapter, newest first; each
    refers to its own instant (R5.1.1, ADR fonte-whale-con-adapter-arkham)."""

    def __init__(self, whales: WhaleTransfersPort, cycle_minutes: int) -> None:
        self._whales = whales
        self._interval = timedelta(minutes=cycle_minutes)

    def execute(self, command: SourceRequest) -> tuple[SourceValue, ...]:
        minimum_usd = command.settings[MINIMUM_USD]
        answered = self._whales.transfers(command.now - self._interval, command.now, minimum_usd, command.credentials)
        return tuple(_value_of(transfer) for transfer in large_transfers(answered, minimum_usd))


def _value_of(transfer: WhaleTransfer) -> SourceValue:
    values = {
        "data_ora": transfer.at.isoformat(),
        "asset": transfer.asset,
        "quantita": _plain(transfer.quantity),
        "controvalore_usd": _plain(transfer.usd_value),
    }
    description = transfer.description
    if description is not None:
        values["descrizione"] = description
    return SourceValue(transfer.at, values)


def _plain(amount: Decimal) -> str:
    """The amount as a person writes it, without exponent nor trailing zeros."""
    return format(amount.normalize(), "f")
