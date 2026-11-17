import hmac
import logging
import threading
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.account_activity import AccountActivityResponse, AccountTransferResponse
from autotrading.adapters.inbound.api.account_state import AccountStateResponse
from autotrading.adapters.inbound.api.cycles import CycleDetailResponse
from autotrading.adapters.inbound.api.errors import install_error_responses
from autotrading.adapters.inbound.api.order_outcome import OrderOutcomeResponse
from autotrading.adapters.inbound.api.verification_run import VerificationRunResponse
from autotrading.adapters.inbound.api.worker_model_catalog import WorkerModelCatalogResponse
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.application.agent.read_model_catalog import ReadModelCatalogUseCase
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_transfers import (
    ReadAccountTransfersCommand,
    ReadAccountTransfersUseCase,
)
from autotrading.application.flows.record_account_executions import (
    RecordAccountExecutionsCommand,
    RecordAccountExecutionsUseCase,
)
from autotrading.application.flows.run_cycle_on_demand import RunCycleOnDemandCommand, RunCycleOnDemandUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import BotInboxPort, BotStartLinkPort
from autotrading.application.notifications.send_test_email import SendTestEmailUseCase
from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.tenancy.errors import NotAuthenticatedError
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationCommand,
    RunExchangeVerificationUseCase,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.notifications.flow_status import FlowStatusLine
from autotrading.domain.notifications.notification import Notification, NotificationLine
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.notifications.notification_target import NotificationTarget, TargetKind
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

BEARER_PREFIX = "bearer "
BOT_PAUSE_SECONDS = 5.0
# Well under the punctuality of a cycle (R1.2.1): a cycle starts within seconds of its planned instant.
CYCLE_PAUSE_SECONDS = 5.0
OUTBOX_PAUSE_SECONDS = 5.0

bot_log = logging.getLogger("autotrading.notifications.bot")
cycles_log = logging.getLogger("autotrading.cycles")
outbox_log = logging.getLogger("autotrading.notifications")


@dataclass(frozen=True, slots=True)
class WorkerUseCases:
    """The use cases of the worker for one request, on adapters bound to the tenant the API names."""

    read_exchange_state: ReadExchangeStateUseCase
    close_exchange_position: CloseExchangePositionUseCase
    run_exchange_verification: RunExchangeVerificationUseCase
    notify: NotifyUseCase
    send_test_email: SendTestEmailUseCase
    read_account_activity: ReadAccountActivityUseCase
    read_account_transfers: ReadAccountTransfersUseCase
    record_account_executions: RecordAccountExecutionsUseCase
    run_cycle_on_demand: RunCycleOnDemandUseCase


@dataclass(frozen=True, slots=True)
class WorkerAnswers:
    """What the worker answers for the whole installation, whatever the tenant: what only it holds."""

    bot_start_link: BotStartLinkPort | None = None
    # The catalog of the gateways whose library only the worker loads (ADR 0148, ADR 0149).
    model_catalog: ReadModelCatalogUseCase | None = None


NO_ANSWERS = WorkerAnswers()


class UserRequest(BaseModel):
    # The API has authenticated the user and sends who asked, so what follows is recorded with them.
    user_id: str


class VerificationRequest(UserRequest):
    # None leaves the value to the minimum of the exchange of the account.
    amount: Decimal | None = Field(default=None, gt=0)


class NotificationLineRequest(BaseModel):
    label: str
    value: str


class NotificationTargetRequest(BaseModel):
    """A page of the dashboard the notification leads to, by what finds it (ADR
    destinazioni-delle-notifiche-nella-dashboard).
    """

    kind: TargetKind
    owner_id: UUID
    asset: str | None = None
    closed_at: datetime | None = None

    def target(self) -> NotificationTarget:
        return NotificationTarget(self.kind, self.owner_id, self.asset, self.closed_at)


class NotificationRequest(BaseModel):
    """Built by the API from its own events: the worker only delivers it to the channels of the tenant, as it is (ADR
    notifica-strutturata-con-icona-titolo-e-valori).
    """

    subject: str
    headline: str
    icon: str
    lines: list[NotificationLineRequest] = Field(default_factory=list)
    flow_status: str | None = None
    # The type of the event; none for the test notification (R3.5.1).
    event: NotificationEvent | None = None
    # The pages it leads to; none from an API that does not send them yet.
    targets: list[NotificationTargetRequest] = Field(default_factory=list)

    def notification(self) -> Notification:
        lines = tuple(NotificationLine(line.label, line.value) for line in self.lines)
        status = None if self.flow_status is None else FlowStatusLine(self.flow_status)
        targets = tuple(target.target() for target in self.targets)
        return Notification(self.subject, self.headline, lines, self.event, self.icon, status, targets)


class BotPolling:
    """Runs the rounds of the Telegram bot in a background thread while the worker is up (ADR 0035).

    A round that fails waits a pause and tries again: Telegram or the database being away never stops the worker.
    """

    thread_name = "telegram-bot"

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


def bot_polling(inbox: BotInboxPort | None, answering: Callable[[BotInboxPort], BotPolling]) -> BotPolling | None:
    """The bot answers only when the installation has one: without its inbox no loop starts (ADR 0035)."""
    return None if inbox is None else answering(inbox)


class CyclePolling:
    """Plans the cycles of every active flow, round after round, while the worker is up (ADR 0042).

    Each round launches the cycles due and returns at once; a failing round is logged and the next one comes after
    the same pause, so the database being away never stops the worker.
    """

    thread_name = "cycles"

    def __init__(self, plan_round: Callable[[], None], pause_seconds: float = CYCLE_PAUSE_SECONDS) -> None:
        self._plan_round = plan_round
        self._pause_seconds = pause_seconds

    def run(self, stopping: threading.Event) -> None:
        while not stopping.is_set():
            try:
                self._plan_round()
            except AutotradingError:
                cycles_log.warning("giro di pianificazione dei cicli fallito", exc_info=True)
            stopping.wait(self._pause_seconds)


class OutboxProcessing:
    """Delivers the messages of the outbox in a background thread while the worker is up (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate).

    Processing lasts as long as the worker; when the queue cannot be served it is recorded and starts again after a
    pause, so the database being away never stops the worker.
    """

    thread_name = "outbox"

    def __init__(self, process: Callable[[], None], pause_seconds: float = OUTBOX_PAUSE_SECONDS) -> None:
        self._process = process
        self._pause_seconds = pause_seconds

    def run(self, stopping: threading.Event) -> None:
        while not stopping.is_set():
            try:
                self._process()
            except AutotradingError:
                outbox_log.warning("consegna dei messaggi in uscita interrotta", exc_info=True)
            stopping.wait(self._pause_seconds)


type BackgroundLoop = BotPolling | CyclePolling | OutboxProcessing


@dataclass(frozen=True, slots=True)
class WorkerLoops:
    """What the worker runs in the background while it is up: each loop only when the installation composes it."""

    bot: BotPolling | None = None
    cycles: CyclePolling | None = None
    outbox: OutboxProcessing | None = None

    def composed(self) -> list[BackgroundLoop]:
        return [loop for loop in (self.bot, self.cycles, self.outbox) if loop is not None]


NO_LOOPS = WorkerLoops()


def background(loops: Sequence[BackgroundLoop]) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Each loop in a thread of its own for the life of the worker, told to stop when the worker stops."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        stopping = threading.Event()
        for loop in loops:
            threading.Thread(target=loop.run, args=(stopping,), name=loop.thread_name, daemon=True).start()
        yield
        stopping.set()

    return lifespan


class StartLinkResponse(BaseModel):
    """The link that opens the platform bot with a link code; none while the worker runs without a bot (R1.8.1)."""

    link: str | None


def create_worker_api(
    token: str,
    for_tenant: Callable[[TenantId], WorkerUseCases],
    loops: WorkerLoops = NO_LOOPS,
    answers: WorkerAnswers = NO_ANSWERS,
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
        lifespan=background(loops.composed()),
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
        command = account_id
        return AccountActivityResponse.of(for_tenant(TenantId(tenant_id)).read_account_activity.execute(command))

    @api.get("/tenants/{tenant_id}/accounts/{account_id}/transfers", dependencies=[Depends(require_api)])
    def read_transfers(
        tenant_id: UUID, account_id: UUID, since: datetime | None = None, until: datetime | None = None
    ) -> list[AccountTransferResponse]:
        """The deposits and withdrawals of the account in the window, for its history of the capital (ADR
        storico-delle-variazioni-di-capitale): only the worker opens an account to read it on its exchange."""
        transfers = for_tenant(TenantId(tenant_id)).read_account_transfers.execute(
            ReadAccountTransfersCommand(account_id, TimeWindow(since, until))
        )
        return [AccountTransferResponse.of(transfer) for transfer in transfers]

    @api.post("/tenants/{tenant_id}/accounts/{account_id}/ledger", dependencies=[Depends(require_api)])
    def record_ledger(tenant_id: UUID, account_id: UUID) -> dict[str, int]:
        """What the exchange added to the account enters its ledger, for a command of the API (ADR incasso-dei-
        profitti): only the worker reads the executions of an account."""
        command = RecordAccountExecutionsCommand(account_id)
        recorded = for_tenant(TenantId(tenant_id)).record_account_executions.execute(command)
        return {"recorded": len(recorded.entries)}

    @api.post("/tenants/{tenant_id}/accounts/{account_id}/positions/{coin}/close", dependencies=[Depends(require_api)])
    def close_position(tenant_id: UUID, account_id: UUID, coin: str, request: UserRequest) -> OrderOutcomeResponse:
        command = CloseExchangePositionCommand(account_id, coin, OrderSource(OrderOrigin.MANUAL, request.user_id))
        order = for_tenant(TenantId(tenant_id)).close_exchange_position.execute(command)
        return OrderOutcomeResponse.of(OrderOutcome.of(order))

    @api.post("/tenants/{tenant_id}/flows/{flow_id}/cycles", dependencies=[Depends(require_api)])
    def run_cycle_now(tenant_id: UUID, flow_id: UUID) -> CycleDetailResponse:
        """A cycle of the flow now, the same as a planned one, answered when it ends (ADR
        ciclo-su-richiesta-nel-worker): a failed cycle is its record, a refusal is a Problem Details."""
        command = RunCycleOnDemandCommand(flow_id)
        return CycleDetailResponse.of(for_tenant(TenantId(tenant_id)).run_cycle_on_demand.execute(command))

    @api.post("/tenants/{tenant_id}/notifications", dependencies=[Depends(require_api)])
    def notify(tenant_id: UUID, request: NotificationRequest) -> dict[str, str]:
        for_tenant(TenantId(tenant_id)).notify.execute(request.notification())
        return {"status": "ok"}

    @api.post("/tenants/{tenant_id}/notifications/email/test", dependencies=[Depends(require_api)], status_code=204)
    def send_test_email(tenant_id: UUID) -> None:
        """The test email now, from the mail server of the tenant, whose password only the worker opens (ADR
        invio-dal-server-di-posta-del-tenant): a refusal of the server is a Problem Details."""
        for_tenant(TenantId(tenant_id)).send_test_email.execute()

    @api.post("/tenants/{tenant_id}/accounts/{account_id}/verifications", dependencies=[Depends(require_api)])
    def run_verification(tenant_id: UUID, account_id: UUID, request: VerificationRequest) -> VerificationRunResponse:
        command = RunExchangeVerificationCommand(account_id, UserId(request.user_id), request.amount)
        run = for_tenant(TenantId(tenant_id)).run_exchange_verification.execute(command)
        return VerificationRunResponse.of(run)

    @api.get("/bot/start-link", dependencies=[Depends(require_api)])
    def read_bot_start_link(code: str) -> StartLinkResponse:
        bot_start_link = answers.bot_start_link
        return StartLinkResponse(link=None if bot_start_link is None else bot_start_link.start_link(code))

    _add_model_catalog(api, require_api, answers.model_catalog)

    @api.get("/health")
    def read_health() -> dict[str, str]:
        return {"status": "ok"}

    return api


def _add_model_catalog(
    api: FastAPI, require_api: Callable[[Request], None], model_catalog: ReadModelCatalogUseCase | None
) -> None:
    """Outside any tenant: the catalog is the same for everyone (ADR 0149). A worker without it does not offer it."""
    if model_catalog is None:
        return

    @api.get("/internal/model-catalog", dependencies=[Depends(require_api)])
    def read_model_catalog() -> WorkerModelCatalogResponse:
        return WorkerModelCatalogResponse.of(model_catalog.execute())
