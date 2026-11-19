from collections.abc import Mapping
from datetime import datetime

import httpx

from autotrading.application.sources.errors import SourceTrialWorkerUnavailableError
from autotrading.domain.sources.errors import InvalidSourceTrialError
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.source_trial import SourceTrial, TrialOutcome
from autotrading.domain.tenancy.tenant_id import TenantId

# The worker waits for the source up to a minute, as a cycle does (R1.2.5): the call waits a little longer.
TIMEOUT_SECONDS = 90.0


class WorkerSourceTrialAdapter:
    """Asks the worker, over the internal network of the installation, to try an adapter of a source now (ADR
    prova-di-un-adapter-di-fonte-nel-worker): only the worker opens the credentials of the adapters.

    Bound to the tenant of the request. The API refuses what the worker would refuse before asking it, so any answer
    other than the trial, or a worker not reachable, is a worker not available.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"WorkerSourceTrialAdapter(tenant_id={self._tenant_id.value})"

    def try_adapter(self, source: str, adapter: str, asset: str | None, parameters: Mapping[str, int]) -> SourceTrial:
        path = f"/tenants/{self._tenant_id.value}/sources/{source}/adapters/{adapter}/trials"
        try:
            response = self._client.post(
                path,
                json={"asset": asset, "parameters": dict(parameters)},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise SourceTrialWorkerUnavailableError from error
        if response.status_code != httpx.codes.OK:
            raise SourceTrialWorkerUnavailableError
        return _trial_of(response)


def _trial_of(response: httpx.Response) -> SourceTrial:
    try:
        body = response.json()
        return SourceTrial(
            outcome=TrialOutcome(body["outcome"]),
            values=tuple(
                SourceValue(datetime.fromisoformat(item["reference_at"]), dict(item["values"]))
                for item in body["values"]
            ),
            response_milliseconds=int(body["response_milliseconds"]),
            reason=body["reason"],
            permanent=bool(body["permanent"]),
        )
    except (KeyError, TypeError, ValueError, InvalidSourceTrialError) as error:
        raise SourceTrialWorkerUnavailableError from error
