"""The maximum loss of a flow at the risk step of its cycles, on the cycles the worker runs, and the suspension of its
openings the user reads and resumes (R3.2.2).

ADR-perdita-massima-sui-valori-di-equity-registrati: the references come from the recorded equities brought to the
capital of now, the suspension is saved beside the flow and blocks only the openings of the risk check.
playwright-bdd runs the scenario of the dashboard on its build (ADR 0116).
"""

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.application.flows.resume_flow_openings import ResumeFlowOpeningsCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.loss_guard import LossGuard
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.openings_suspension import OpeningsSuspension, day_start
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.support.activity import a_position, an_activity
from tests.support.decision_steps import answer, decision, opening
from tests.support.flow_cycle_steps import position
from tests.support.flow_cycles import DAY, FlowCycles
from tests.support.notifications import chat_named, told_in
from tests.support.platform import HYPERLIQUID
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.2-limiti-di-rischio/R3.2.2-perdita-massima-del-flusso.feature")

FLOW = "alfa"
CAPITAL = Decimal(1000)
MIDNIGHT = DAY
# The flow started days before the scenario, so its peak counts from before today.
FIRST_START = DAY - timedelta(days=3)
SUSPENDED = "perdita giornaliera 6% oltre il 5%"
RESUMES = {"manuale": OpeningsResume.MANUAL, "il giorno dopo": OpeningsResume.NEXT_DAY}


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


class MaximumLoss:
    """The flow of the scenario: its value, its recorded equities, its openings and what the user was refused."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles
        self.user = ""
        self.value = CAPITAL
        self.refusals: list[AutotradingError] = []
        self.seen: OpeningsSuspension | None = None

    @property
    def tenant_id(self) -> TenantId:
        return self.flow_cycles.platform.tenant_of(self.user)

    @property
    def flow_id(self) -> FlowId:
        return self.flow_cycles.flow(FLOW).id

    def now(self) -> datetime:
        return self.flow_cycles.clock.now()

    def at(self, instant: datetime) -> None:
        """The worker and the API read the same instant."""
        self.flow_cycles.clock.current = instant
        self.flow_cycles.platform.now = instant

    def recorded(self, planned_at: datetime, equity: Decimal) -> None:
        """An equity a past cycle recorded, at the capital of the flow then."""
        snapshot = EquitySnapshot(
            self.flow_id.value, planned_at, CAPITAL, equity - CAPITAL, Decimal(0), Decimal(0), Decimal(0)
        )
        InMemoryEquitySnapshotRepositoryAdapter(self.flow_cycles.equity_snapshots, self.tenant_id).record(snapshot)

    def worth(self, value: Decimal) -> None:
        """The value of the flow now: its capital and what its closed trades earned."""
        self.value = value
        capital = self.flow_cycles.flow(FLOW).configuration.assigned_capital
        totals = self.flow_cycles.platform.ledger.totals
        totals[self.flow_id] = replace(totals.get(self.flow_id, FlowTotals(self.flow_id)), realized_pnl=value - capital)

    def run_cycle(self) -> None:
        self.at(self.now())
        self.flow_cycles.run(FLOW)

    def suspend(self, reason: str = SUSPENDED) -> None:
        openings = InMemoryOpeningsSuspensionAdapter(self.flow_cycles.platform.flows, self.tenant_id)
        openings.suspend(self.flow_id.value, OpeningsSuspension(reason, self.now()))

    def suspended_by_a_cycle(self) -> None:
        self.recorded(MIDNIGHT, CAPITAL)
        self.worth(Decimal(940))
        self.run_cycle()
        assert self.suspension() is not None

    def suspension(self) -> OpeningsSuspension | None:
        self.flow_cycles.platform.now = self.now()
        use_cases = self.flow_cycles.platform.use_cases_of(self.user)
        return use_cases.read_flow_results.execute(ReadFlowResultsCommand(self.flow_id.value)).openings_suspension

    def peak(self) -> Decimal:
        """The peak the guard of the losses measures from now, with the value of the flow now."""
        flow = self.flow_cycles.flow(FLOW)
        openings = InMemoryOpeningsSuspensionAdapter(self.flow_cycles.platform.flows, self.tenant_id)
        status = openings.status(flow.id.value).at(self.now(), flow.configuration.openings_resume)
        equities = InMemoryEquitySnapshotRepositoryAdapter(self.flow_cycles.equity_snapshots, self.tenant_id)
        now = self.now()
        references = equities.loss_references(flow.id.value, day_start(now), status.peak_since(FIRST_START), now)
        return LossGuard.of(flow.configuration, self.value, references).peak

    def modify(self, user: str, command: ModifyFlowCommand) -> None:
        try:
            self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
        except AutotradingError as error:
            self.refusals.append(error)

    def suspension_notices(self) -> list[str]:
        received = self.flow_cycles.platform.messenger.received_by(chat_named(self.user))
        return [text for text in received if "aperture sospese" in text]

    def outcomes(self) -> list[dict[str, object]]:
        document = self.flow_cycles.last_record(FLOW).document(CycleStep.RISK_CHECK)
        assert document is not None
        outcomes = document["esiti"]
        assert isinstance(outcomes, list)
        return outcomes

    def outcome_of(self, asset: str) -> dict[str, object]:
        [outcome] = [outcome for outcome in self.outcomes() if outcome["asset"] == asset]
        return outcome

    def sent_on(self, asset: str) -> bool:
        return asset in {order.coin for order in self.flow_cycles.platform.order_exchange.sent}


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def loss(flow_cycles: FlowCycles) -> MaximumLoss:
    return MaximumLoss(flow_cycles)


# Given


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "alfa" attivo con asset "(?P<asset>[^"]+)", perdita giornaliera '
        r'massima (?P<daily>[\d,]+)%, perdita massima dal picco (?P<peak>[\d,]+)% e ripresa "(?P<resume>[^"]+)"$'
    )
)
def flow_with_maximum_losses(loss: MaximumLoss, user: str, asset: str, *, daily: str, peak: str, resume: str) -> None:
    cycles = loss.flow_cycles
    loss.user = user
    flow = cycles.add_flow(user, FLOW, assets=(asset,))
    cycles.platform.flows.first_starts[flow.id] = FIRST_START
    cycles.reconfigure(
        FLOW,
        lambda configuration: replace(
            configuration,
            allocated_capital=CAPITAL,
            max_daily_loss_percent=amount(daily),
            max_drawdown_percent=amount(peak),
            openings_resume=RESUMES[resume],
        ),
    )
    tenant_id = cycles.platform.tenant_of(user)
    cycles.platform.chats[tenant_id] = LinkedChat(tenant_id, chat_named(user))
    loss.at(cycles.clock.now())


@given(parsers.re(r'^che alle 00:00 UTC di oggi il valore di "alfa" era (?P<value>[\d,]+) USDC$'))
def value_at_midnight(loss: MaximumLoss, value: str) -> None:
    loss.recorded(MIDNIGHT, amount(value))


@given(parsers.re(r'^che il valore più alto raggiunto da "alfa" è (?P<value>[\d,]+) USDC$'))
def highest_value(loss: MaximumLoss, value: str) -> None:
    loss.recorded(MIDNIGHT - timedelta(hours=12), amount(value))


@given(
    parsers.re(
        r'^che alle 00:00 UTC di oggi il valore di "alfa" era (?P<midnight>[\d,]+) USDC '
        r"e il valore più alto raggiunto è (?P<highest>[\d,]+) USDC$"
    )
)
def value_at_midnight_and_highest(loss: MaximumLoss, midnight: str, highest: str) -> None:
    loss.recorded(MIDNIGHT - timedelta(hours=12), amount(highest))
    loss.recorded(MIDNIGHT, amount(midnight))


@given('che le aperture di "alfa" sono sospese per perdita massima')
def openings_suspended(loss: MaximumLoss) -> None:
    loss.suspend()


@given(quoted('che le aperture di "alfa" sono sospese con motivo "{reason}"'))
def openings_suspended_with_reason(loss: MaximumLoss, reason: str) -> None:
    loss.suspend(reason)


@given(quoted('che "alfa" ha una posizione aperta su "{asset}"'))
def open_position(loss: MaximumLoss, asset: str) -> None:
    cycles = loss.flow_cycles
    size = Decimal("0.01")
    credentials = cycles.credentials_of(FLOW)
    cycles.platform.hyperliquid.open_position(credentials, position(asset, size=size))
    # The account reads the position from the market data, the orders close it on the exchange of the orders.
    cycles.platform.order_exchange.hold(
        TradingAccess(HYPERLIQUID, credentials.values), HeldPosition(asset, Direction.LONG, size, 1, Decimal(100))
    )
    address = credentials.value("account_address")
    cycles.platform.activity_reader.activities[address] = an_activity(positions=(a_position(asset, size=size),))
    cycles.platform.ledger.expect(loss.flow_id, asset, size)


@given(quoted('che le aperture di "alfa" sono sospese per perdita massima e "{user}" ne ha ricevuto la notifica'))
def openings_suspended_and_told(loss: MaximumLoss, user: str) -> None:
    loss.suspended_by_a_cycle()
    assert len(loss.suspension_notices()) == 1, user


@given(parsers.re(r'^che le aperture di "alfa" sono sospese per perdita massima e il valore di "alfa" è 940 USDC$'))
def openings_suspended_at_940(loss: MaximumLoss) -> None:
    loss.suspended_by_a_cycle()


@given(quoted('che "alfa" ha ripresa "{resume}"'))
def flow_with_resume(loss: MaximumLoss, resume: str) -> None:
    loss.flow_cycles.reconfigure(FLOW, lambda configuration: replace(configuration, openings_resume=RESUMES[resume]))


# When


@when(parsers.re(r'^un ciclo di "alfa" legge il valore (?P<value>[\d,]+) USDC$'))
def cycle_reads_value(loss: MaximumLoss, value: str) -> None:
    loss.worth(amount(value))
    loss.run_cycle()


@when(quoted('l\'agente di "alfa" decide di aprire long su "{asset}"'))
def agent_opens(loss: MaximumLoss, asset: str) -> None:
    answer(loss.flow_cycles, opening(asset))
    loss.run_cycle()


@when(quoted('l\'agente di "alfa" decide di chiudere la posizione su "{asset}"'))
def agent_closes(loss: MaximumLoss, asset: str) -> None:
    answer(loss.flow_cycles, decision(asset, "chiudi"))
    loss.run_cycle()


@when('parte il ciclo successivo di "alfa" con la soglia ancora superata')
def next_cycle_still_beyond(loss: MaximumLoss) -> None:
    loss.at(loss.now() + timedelta(minutes=15))
    loss.run_cycle()


@when(quoted('"{user}" conferma la ripresa delle aperture di "alfa"'))
def user_resumes(loss: MaximumLoss, user: str) -> None:
    loss.at(loss.now() + timedelta(minutes=1))
    try:
        loss.flow_cycles.platform.use_cases_of(user).resume_flow_openings.execute(
            ResumeFlowOpeningsCommand(loss.flow_id)
        )
    except AutotradingError as error:
        loss.refusals.append(error)


@when("arrivano le 00:00 UTC del giorno successivo")
def next_midnight(loss: MaximumLoss) -> None:
    loss.at(MIDNIGHT + timedelta(days=1))


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" riduce di (?P<reduction>[\d,]+) USDC il capitale allocato di "alfa" '
        r"e un ciclo legge il valore (?P<value>[\d,]+) USDC$"
    )
)
def capital_reduced(loss: MaximumLoss, user: str, reduction: str, value: str) -> None:
    platform = loss.flow_cycles.platform
    command = ChangeAllocatedCapitalCommand(loss.flow_id, CAPITAL - amount(reduction), platform.user_id_of(user))
    platform.use_cases_of(user).change_allocated_capital.execute(command)
    loss.worth(amount(value))
    loss.run_cycle()


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" aumenta di (?P<increase>[\d,]+) USDC il capitale allocato di "alfa" '
        r"e un ciclo legge il valore (?P<value>[\d,]+) USDC$"
    )
)
def capital_increased(loss: MaximumLoss, user: str, increase: str, value: str) -> None:
    platform = loss.flow_cycles.platform
    command = ChangeAllocatedCapitalCommand(loss.flow_id, CAPITAL + amount(increase), platform.user_id_of(user))
    platform.use_cases_of(user).change_allocated_capital.execute(command)
    loss.worth(amount(value))
    loss.run_cycle()


@when(quoted('l\'agente di "alfa" decide di aggiornare lo stop su "{asset}" a {stop}'))
def agent_updates_stop(loss: MaximumLoss, asset: str, stop: str) -> None:
    fields = {"direzione": None, "quota": None, "leva": None, "obiettivo": None, "invalidazione": None}
    update = {**decision(asset, "aggiorna"), **fields, "stop": int(stop), "togli_obiettivo": False}
    answer(loss.flow_cycles, update)
    loss.run_cycle()


@when(quoted('"{user}" imposta la ripresa di "alfa" a "{resume}"'))
def set_resume(loss: MaximumLoss, user: str, resume: str) -> None:
    loss.modify(user, ModifyFlowCommand(loss.flow_id, openings_resume=RESUMES[resume]))


@when(quoted('"{user}" imposta la perdita {threshold} di "alfa" a {value}%'))
def set_threshold(loss: MaximumLoss, user: str, threshold: str, value: str) -> None:
    percent = amount(value)
    command = (
        ModifyFlowCommand(loss.flow_id, max_daily_loss_percent=percent)
        if threshold == "giornaliera massima"
        else ModifyFlowCommand(loss.flow_id, max_drawdown_percent=percent)
    )
    try:
        loss.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
    except AutotradingError as error:
        loss.refusals.append(error)


@when(quoted('"{user}" apre il flusso "alfa" nella dashboard'))
def opens_flow_page(loss: MaximumLoss, user: str) -> None:
    loss.user = user
    loss.seen = loss.suspension()


# Then


@then(quoted('le aperture di "alfa" sono sospese con motivo "{reason}"'))
def suspended_with_reason(loss: MaximumLoss, reason: str) -> None:
    suspension = loss.suspension()
    assert suspension is not None
    assert suspension.reason == reason


@then(quoted('"{user}" riceve la notifica "{title}" con le righe "{values}"'))
def notified(loss: MaximumLoss, user: str, title: str, values: str) -> None:
    received = loss.flow_cycles.platform.messenger.received_by(chat_named(user))
    assert told_in(received, title, values), received


@then('le aperture di "alfa" non sono sospese')
def not_suspended(loss: MaximumLoss) -> None:
    assert loss.suspension() is None
    assert loss.refusals == []


@then('le aperture di "alfa" restano sospese')
def still_suspended(loss: MaximumLoss) -> None:
    assert loss.suspension() == OpeningsSuspension(SUSPENDED, DAY.replace(hour=10))


@then(quoted('"alfa" non apre la posizione su "{asset}"'))
def not_opened(loss: MaximumLoss, asset: str) -> None:
    assert loss.outcome_of(asset)["tipo"] == "BlockedDecision"
    assert not loss.sent_on(asset)


@then(quoted('il ciclo di "alfa" registra "{text}"'))
def cycle_records(loss: MaximumLoss, text: str) -> None:
    assert text in [outcome.get("reason") for outcome in loss.outcomes()], loss.outcomes()


@then(quoted('"alfa" chiude la posizione su "{asset}"'))
def closed(loss: MaximumLoss, asset: str) -> None:
    assert loss.outcome_of(asset)["tipo"] == "ApprovedClose"
    assert loss.sent_on(asset)


@then(quoted('"{user}" non riceve un\'altra notifica di sospensione'))
def no_other_notice(loss: MaximumLoss, user: str) -> None:
    assert loss.user == user
    assert len(loss.suspension_notices()) == 1
    assert loss.suspension() is not None


@then(parsers.re(r'^il picco di "alfa" riparte da (?P<value>[\d,]+) USDC$'))
def peak_restarts(loss: MaximumLoss, value: str) -> None:
    assert loss.peak() == amount(value)


@then(quoted('il comando viene rifiutato con "{reason}"'))
def command_refused(loss: MaximumLoss, reason: str) -> None:
    assert [str(error) for error in loss.refusals] == [reason]


@then(quoted('la modifica viene rifiutata con "{reason}"'))
def modification_refused(loss: MaximumLoss, reason: str) -> None:
    assert [str(error) for error in loss.refusals] == [reason]
    configuration = loss.flow_cycles.flow(FLOW).configuration
    assert (configuration.version, configuration.max_daily_loss_percent, configuration.max_drawdown_percent) == (
        1,
        Decimal(5),
        Decimal(10),
    )


@then(quoted('"alfa" aggiorna il piano di uscita della posizione su "{asset}"'))
def plan_updated(loss: MaximumLoss, asset: str) -> None:
    assert loss.outcome_of(asset)["tipo"] == "ApprovedUpdate"


@then(
    parsers.re(
        r'^la configurazione di "alfa" passa alla versione (?P<version>\d+) con perdita giornaliera massima '
        r"(?P<value>[\d,]+)%$"
    )
)
def new_version_with_daily_loss(loss: MaximumLoss, version: str, value: str) -> None:
    assert loss.refusals == []
    configuration = loss.flow_cycles.flow(FLOW).configuration
    assert (configuration.version, configuration.max_daily_loss_percent) == (int(version), amount(value))


@then(quoted('la configurazione di "alfa" passa alla versione {version} con ripresa "{resume}"'))
def new_version_with_resume(loss: MaximumLoss, version: str, resume: str) -> None:
    assert loss.refusals == []
    configuration = loss.flow_cycles.flow(FLOW).configuration
    assert (configuration.version, configuration.openings_resume) == (int(version), RESUMES[resume])


@then(quoted('la pagina mostra "{notice}" e il comando "{command}"'))
def page_shows(loss: MaximumLoss, notice: str, command: str) -> None:
    # What the page shows comes from the API: the suspension in force, which the command resumes (ADR 0116).
    assert loss.seen is not None
    assert notice == f"aperture sospese: {loss.seen.reason}"
    assert command == "Riprendi le aperture"
