import hmac
import logging
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from autotrading.adapters.inbound.api.account_activity import AccountActivityResponse
from autotrading.adapters.inbound.api.account_state import AccountStateResponse
from autotrading.adapters.inbound.api.errors import NotAuthenticatedError, install_error_responses
from autotrading.adapters.inbound.api.order_outcome import OrderOutcomeResponse
from autotrading.adapters.inbound.api.verification_run import VerificationRunResponse
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.application.flows.read_account_activity import (
    ReadAccountActivityCommand,
    ReadAccountActivityUseCase,
)
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.outcome import OrderOutcome
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationCommand,
    RunExchangeVerificationUseCase,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

BEARER_PREFIX = "bearer "
BOT_PAUSE_SECONDS = 5.0

bot_log = logging.getLogger("autotrading.notifications.bot")


@dataclass(frozen=True, slots=True)
class WorkerUseCases:
    """The use cases of the worker for one request, on adapters bound to the tenant the API names."""

    read_exchange_state: ReadExchangeStateUseCase
    close_exchange_position: CloseExchangePositionUseCase
    run_exchange_verification: RunExchangeVerificationUseCase
    notify: NotifyUseCase
    read_account_activity: ReadAccountActivityUseCase


class UserRequest(BaseModel):
    # The API has authenticated the user and sends who asked, so what follows is recorded with them.
    user_id: str


class BotPolling:
    """Runs the rounds of the Telegram bot in a background thread while the worker is up (ADR 0035).

    A round that fails waits a pause and tries again: Telegram or the database being away never stops the worker.
    """

    def __init__(self, answer_round: Callable[[], None], pause_seconds: float = BOT_PAUSE_SECONDS) -> None:
        self._answer_round = answer_round
        self._pause_seconds = pause_seconds

    def run(self, stopping: threading.Event) -> None:
        while not stopping.is_set():
            try:
                self._answer_round()
            except AutotradingError:
                bot_log.warning("giro del bot Telegram fallito", exc_info=True)
                stopping.wait(self._pause_seconds)

    @asynccontextmanager
    async def lifespan(self, _: FastAPI) -> AsyncIterator[None]:
        stopping = threading.Event()
        threading.Thread(target=self.run, args=(stopping,), name="telegram-bot", daemon=True).start()
        yield
        stopping.set()


def create_worker_api(
    token: str, for_tenant: Callable[[TenantId], WorkerUseCases], bot: BotPolling | None = None
) -> FastAPI:
    """The internal service of the worker: reachable only by the API on the network of the installation (ADR 0021).

    The tenant travels in the path because the API has already resolved it from the identity of the user; the
    worker trusts it only from a caller holding the token generated on the machine.
    """
    api = FastAPI(
        title="AutoTrading worker",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=None if bot is None else bot.lifespan,
    )
    install_error_responses(api)

    def require_api(request: Request) -> None:
        authorization = request.headers.get("Authorization", "")
        presented = authorization[len(BEARER_PREFIX) :] if authorization.lower().startswith(BEARER_PREFIX) else ""
        # An empty token never matches, even if the worker was started without one.
        if not presented or not hmac.compare_digest(presented.encode(), token.encode()):
            raise NotAuthenticatedError

    @api.get("/tenants/{tenant_id}/accounts/{account_id}/state", dependencies=[Depends(require_api)])
    def read_state(tenant_id: UUID, account_id: UUID) -> AccountStateResponse:
        command = ReadExchangeStateCommand(AccountId(account_id))
        return AccountStateResponse.of(for_tenant(TenantId(tenant_id)).read_exchange_state.execute(command))

    @api.get("/tenants/{tenant_id}/accounts/{account_id}/activity", dependencies=[Depends(require_api)])
    def read_activity(tenant_id: UUID, account_id: UUID) -> AccountActivityResponse:
        command = ReadAccountActivityCommand(account_id)
        return AccountActivityResponse.of(for_tenant(TenantId(tenant_id)).read_account_activity.execute(command))

    @api.post("/tenants/{tenant_id}/accounts/{account_id}/positions/{coin}/close", dependencies=[Depends(require_api)])
    def close_position(tenant_id: UUID, account_id: UUID, coin: str, request: UserRequest) -> OrderOutcomeResponse:
        command = CloseExchangePositionCommand(account_id, coin, OrderSource(OrderOrigin.MANUAL, request.user_id))
        order = for_tenant(TenantId(tenant_id)).close_exchange_position.execute(command)
        return OrderOutcomeResponse.of(OrderOutcome.of(order))

    @api.post("/tenants/{tenant_id}/accounts/{account_id}/verifications", dependencies=[Depends(require_api)])
    def run_verification(tenant_id: UUID, account_id: UUID, request: UserRequest) -> VerificationRunResponse:
        command = RunExchangeVerificationCommand(account_id, UserId(request.user_id))
        run = for_tenant(TenantId(tenant_id)).run_exchange_verification.execute(command)
        return VerificationRunResponse.of(run)

    @api.get("/health")
    def read_health() -> dict[str, str]:
        return {"status": "ok"}

    return api
