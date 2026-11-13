from collections.abc import Callable

import httpx

from autotrading.adapters.outbound.worker.account_activity import WorkerAccountActivityAdapter
from autotrading.adapters.outbound.worker.account_state import WorkerAccountStateAdapter
from autotrading.adapters.outbound.worker.bot_identity import WorkerBotIdentityAdapter
from autotrading.adapters.outbound.worker.configuration import _WorkerSettings
from autotrading.adapters.outbound.worker.notifications import WorkerNotificationAdapter
from autotrading.adapters.outbound.worker.position_closing import WorkerPositionClosingAdapter
from autotrading.adapters.outbound.worker.verification import WorkerVerificationAdapter
from autotrading.domain.tenancy.tenant_id import TenantId

type WorkerAdaptersOfTenant = tuple[
    WorkerBotIdentityAdapter,
    WorkerAccountStateAdapter,
    WorkerAccountActivityAdapter,
    WorkerPositionClosingAdapter,
    WorkerVerificationAdapter,
    WorkerNotificationAdapter,
]


def worker_adapters(
    url: str, token: str, transport: httpx.BaseTransport | None = None
) -> Callable[[TenantId], WorkerAdaptersOfTenant]:
    """One client for the installation; for each request, the adapters bound to its tenant (ADR 0021)."""
    settings = _WorkerSettings(url, token)
    client = httpx.Client(base_url=settings.url, timeout=settings.timeout_seconds, transport=transport)
    # One per installation: the start link is the same for every tenant.
    start_link = WorkerBotIdentityAdapter(client, settings.token)

    def adapters_of(tenant_id: TenantId) -> WorkerAdaptersOfTenant:
        return (
            start_link,
            WorkerAccountStateAdapter(client, settings.token, tenant_id),
            WorkerAccountActivityAdapter(client, settings.token, tenant_id),
            WorkerPositionClosingAdapter(client, settings.token, tenant_id),
            WorkerVerificationAdapter(client, settings.token, tenant_id),
            WorkerNotificationAdapter(client, settings.token, tenant_id),
        )

    return adapters_of
