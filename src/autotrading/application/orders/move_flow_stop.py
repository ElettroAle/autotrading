from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import SendingRetryPort, StopMovePort
from autotrading.application.orders.sending import RetriedCalls
from autotrading.application.orders.update_flow_protection import (
    UpdateFlowProtectionCommand,
    UpdateFlowProtectionUseCase,
)
from autotrading.domain.orders.flow_order import FlowUpdate
from autotrading.domain.orders.protection_request import ProtectionRequest


class MoveFlowStopUseCase:
    """Moves the stop loss of an open position of a flow closer to the price, between the cycles, with the replacement
    of the update of its exit plan: the new stop is placed before the old one goes, and recorded (R5.5.1, ADR
    sorveglianza-del-prezzo-per-lo-stop-che-segue).

    The refusal of the exchange comes back as the cycle records it, the stop in force left as it was. A temporary error
    is tried again as the retry given allows; one that stays comes out.
    """

    def __init__(
        self, access: OpenTradingAccessUseCase, update: UpdateFlowProtectionUseCase, retry: SendingRetryPort
    ) -> None:
        self._access = access
        self._update = update
        self._retry = retry

    def execute(self, move: StopMovePort) -> str | None:
        access = self._access.execute(OpenTradingAccessCommand(move.account_id))
        # The stop the platform computes lies closer to the price than the one in force: the default stop is the bound
        # every stop keeps, never the level here.
        protection = ProtectionRequest(move.stop, None, move.default_stop_loss_percent, None)
        update = FlowUpdate(move.asset, protection, remove_target=False)
        command = UpdateFlowProtectionCommand(access, move.account_id, move.flow_id, update, RetriedCalls(self._retry))
        notes = self._update.execute(command)
        return next((note.text for note in notes if note.refused), None)
