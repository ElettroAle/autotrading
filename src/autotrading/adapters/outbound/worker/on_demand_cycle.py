from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

import httpx

from autotrading.application.flows.errors import (
    CycleInProgressError,
    CycleWorkerUnavailableError,
    FlowNotActiveError,
    FlowNotFoundError,
)
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import AbsentSource, CycleFailure, CycleOutcome, CycleRecord, StepDocument
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.tenancy.tenant_id import TenantId

# The whole cycle runs while the call waits: the sources (up to a minute), the model (up to 120 seconds), the orders.
TIMEOUT_SECONDS = 300.0

# The worker answers both refusals with 409: the reason in the Problem Details tells them apart (ADR 0021).
_CONFLICTS: Mapping[str, type[CycleInProgressError | FlowNotActiveError]] = {
    str(CycleInProgressError()): CycleInProgressError,
    str(FlowNotActiveError()): FlowNotActiveError,
}


class WorkerOnDemandCycleAdapter:
    """Asks the worker, over the internal network of the installation, to run a cycle of a flow now and waits for it
    to end (ADR comando-del-ciclo-su-richiesta-nell-api): only the worker runs the cycles.

    Bound to the tenant of the request. A flow the worker does not find is not found, its refusals become the errors
    of the port again; anything else it cannot answer, or answers in an unexpected shape, is a worker not available.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"WorkerOnDemandCycleAdapter(tenant_id={self._tenant_id.value})"

    def run(self, flow_id: UUID) -> CycleRecord:
        path = f"/tenants/{self._tenant_id.value}/flows/{flow_id}/cycles"
        try:
            response = self._client.post(
                path, headers={"Authorization": f"Bearer {self._token}"}, timeout=TIMEOUT_SECONDS
            )
        except httpx.HTTPError as error:
            raise CycleWorkerUnavailableError from error
        _raise_for_refusal(response)
        return _record_of(flow_id, response)


def _raise_for_refusal(response: httpx.Response) -> None:
    status = response.status_code
    if status == httpx.codes.OK:
        return
    if status == httpx.codes.NOT_FOUND:
        raise FlowNotFoundError
    if status == httpx.codes.CONFLICT:
        raise _conflict_of(_reason_of(response))
    raise CycleWorkerUnavailableError


def _reason_of(response: httpx.Response) -> object:
    try:
        return response.json()["detail"]
    except (KeyError, TypeError, ValueError) as error:
        raise CycleWorkerUnavailableError from error


def _conflict_of(reason: object) -> CycleInProgressError | FlowNotActiveError | CycleWorkerUnavailableError:
    if not isinstance(reason, str) or reason not in _CONFLICTS:
        return CycleWorkerUnavailableError()
    return _CONFLICTS[reason]()


def _record_of(flow_id: UUID, response: httpx.Response) -> CycleRecord:
    try:
        body = response.json()
        failure, cost = body["failure"], body["cost"]
        return CycleRecord(
            flow_id=flow_id,
            planned_at=datetime.fromisoformat(body["planned_at"]),
            outcome=CycleOutcome(body["outcome"]),
            started_at=_instant(body["started_at"]),
            delay_seconds=body["delay_seconds"],
            steps=tuple(CycleStep(step) for step in body["steps"]),
            absent_sources=tuple(AbsentSource(item["source"], item["reason"]) for item in body["absent_sources"]),
            failure=None
            if failure is None
            else CycleFailure(CycleStep(failure["step"]), failure["error_type"], failure["message"]),
            documents=tuple(StepDocument(CycleStep(item["step"]), item["content"]) for item in body["documents"]),
            cost=None
            if cost is None
            else CallCost(cost["input_tokens"], cost["output_tokens"], _decimal(cost["cost_usd"])),
            trigger=CycleTrigger(body["trigger"]),
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise CycleWorkerUnavailableError from error


def _instant(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)
