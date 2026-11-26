from collections.abc import Mapping
from itertools import chain

from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ExchangeConnection, HeldFlowAssetsPort, ProtectionRepositoryPort
from autotrading.application.orders.sending import held_protections, supported_exchange


class RecordWaitingProtectionsUseCase:
    """At the start of every cycle, before the state of the flow is read, a position of the flow without protections
    recorded gets recorded the protections waiting on the exchange, like those the platform places: a position opened
    before the platform recorded its protections shows its stop and target (R5.5.3, ADR
    stop-e-obiettivo-in-vigore-nello-stato-della-posizione).

    A position with protections recorded does not read the exchange. An error of the exchange comes out to the step of
    the cycle, which tries it again; what was recorded before it stays, so the attempt that follows skips it.
    """

    def __init__(
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ExchangeConnection],
        protections: ProtectionRepositoryPort,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._protections = protections

    def execute(self, held: HeldFlowAssetsPort) -> None:
        unrecorded = tuple(asset for asset in held.assets if not self._protections.placed(held.account_id, asset))
        if not unrecorded:
            return
        access = self._access.execute(OpenTradingAccessCommand(held.account_id))
        exchange = supported_exchange(self._exchanges, access.exchange)
        held_positions = (held_protections(exchange, access, asset) for asset in unrecorded)
        positions = (position for position in held_positions if position is not None)
        waiting = (position.recorded_for(held.account_id, held.flow_id) for position in positions)
        for protection in chain.from_iterable(waiting):
            self._protections.add(protection)
