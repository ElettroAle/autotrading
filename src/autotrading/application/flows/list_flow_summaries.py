from collections.abc import Mapping
from datetime import timedelta
from uuid import UUID

from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.ports import FlowAccountNamesPort, FlowRepositoryPort, FlowSummary, FlowTimingPort
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_timing import UNSTAMPED, FlowTiming


class ListFlowSummariesUseCase:
    """The flows in use of the tenant as the consultation of the cycles shows them (R1.7.3, ADR 0042).

    The schedule of a flow starts at its last start or resume, the anchor the database stamps on the flow.
    """

    def __init__(self, flows: FlowRepositoryPort, accounts: FlowAccountNamesPort, timing: FlowTimingPort) -> None:
        self._flows = flows
        self._accounts = accounts
        self._timing = timing

    def execute(self) -> list[FlowSummary]:
        timings = self._timing.timings()
        names = self._accounts.account_names()
        return [
            _summary_of(flow, _account_name(names, flow), timings.get(flow.id, UNSTAMPED))
            for flow in ListFlowsUseCase(self._flows).execute()
        ]


def _account_name(names: Mapping[UUID, str], flow: Flow) -> str:
    """A draft has no account yet: its name is empty, like that of an account no longer listed (ADR 0124)."""
    if flow.account_id is None:
        return ""
    return names.get(flow.account_id, "")


def _summary_of(flow: Flow, account: str, timing: FlowTiming) -> FlowSummary:
    configuration = flow.configuration
    interval = timedelta(minutes=configuration.cycle_interval.minutes)
    return FlowSummary(
        flow_id=flow.id.value,
        name=flow.name.value,
        account=account,
        status=flow.status.value,
        pause_reason=timing.pause_reason,
        model=configuration.model.name,
        schedule=CycleSchedule.planned(flow.status.runs_cycles, timing.anchor, interval),
    )
