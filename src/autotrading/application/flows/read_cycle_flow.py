from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import (
    AccountExposureLimitPort,
    FlowHeldAssets,
    FlowRepositoryPort,
    FlowTimingPort,
    ReconciliationRepositoryPort,
    WaitingProtectionsPort,
)
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateCommand, ReadCycleFlowStateUseCase
from autotrading.domain.flows.account_exposure_reading import AccountExposureReading
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_timing import UNSTAMPED


@dataclass(frozen=True, slots=True)
class ReadCycleFlowCommand:
    """The flow of a cycle, the anchor of its schedule, and whether its account was just reconciled."""

    flow_id: FlowId
    anchor: datetime
    reconciled: bool


@dataclass(frozen=True, slots=True)
class CycleAccountReadings:
    """What a cycle reads of the account of its flow: the account on the exchange, proving its credentials, then the
    protections waiting for the positions without protections recorded (R5.5.3), and the limit of the exposure of its
    flows on one side (R5.5.5).
    """

    account: ReadCycleAccountUseCase
    waiting_protections: WaitingProtectionsPort
    exposure_limits: AccountExposureLimitPort


class ReadCycleFlowUseCase:
    """The flow as a cycle reads it: its configuration in force, its account on the exchange, the state attributed
    to it, the instant it began (R1.2.3, R1.4.3, ADR 0062) and the alarm of reconciliation open on its account
    (R3.3.1).

    The alarm is read after the state, so an alarm the reconciliation of this cycle opened already suspends its
    openings. Between the account, which proves its credentials, and the state, the protections waiting on the exchange
    of a position without protections recorded are recorded, so the state shows the stop and the target in force
    (R5.5.3, ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione).

    The exposure of the account is computed from the same reading of the account, only with a limit on the account or
    with the option of the flow on (R5.5.5, ADR controllo-dell-esposizione-del-conto-nel-rischio).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        timing: FlowTimingPort,
        account: CycleAccountReadings,
        read_state: ReadCycleFlowStateUseCase,
        readings: ReconciliationRepositoryPort,
    ) -> None:
        self._flows = flows
        self._timing = timing
        self._account = account
        self._read_state = read_state
        self._readings = readings

    def execute(self, command: ReadCycleFlowCommand) -> CycleFlow:
        flow = self._flows.get(command.flow_id)
        reading = self._account.account.execute(flow.assigned_account_id)
        self._account.waiting_protections.execute(_held_assets(flow, reading.account))
        attributed = self._read_state.execute(ReadCycleFlowStateCommand(flow.id, command.reconciled))
        alarm = self._readings.open_alarm(flow.assigned_account_id)
        started_at = self._timing.timings().get(flow.id, UNSTAMPED).beginning(command.anchor)
        exposure = self._exposure_of(flow, reading.account)
        return CycleFlow(
            flow.tenant_id,
            flow,
            reading.name,
            reading.exchange,
            started_at,
            reading.account,
            attributed,
            alarm,
            exposure,
        )

    def _exposure_of(self, flow: Flow, account: CycleAccount) -> AccountExposureReading:
        percent = self._account.exposure_limits.max_direction_exposure_percent(flow.assigned_account_id)
        if percent is None and not flow.configuration.account_exposure_for_agent:
            return AccountExposureReading()
        return AccountExposureReading.of(flow, self._flows.list(), account, percent)


def _held_assets(flow: Flow, account: CycleAccount) -> FlowHeldAssets:
    held = flow.configuration.held(account.positions, lambda position: position.asset)
    return FlowHeldAssets(flow.assigned_account_id, flow.id.value, tuple(position.asset for position in held))
