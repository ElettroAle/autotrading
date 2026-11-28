"""A periodic check of the worker, run for every tenant on the ports bound to it."""

from autotrading.application.flows.every_tenant import every_tenant
from autotrading.domain.tenancy.tenant_id import TenantId

ANNA, BRUNO = TenantId.new(), TenantId.new()


class Tenants:
    def __init__(self) -> None:
        self.ids: tuple[TenantId, ...] = (ANNA,)

    def tenant_ids(self) -> tuple[TenantId, ...]:
        return self.ids


def test_the_check_runs_for_every_tenant_of_the_moment_it_runs() -> None:
    tenants, checked = Tenants(), list[TenantId]()
    check = every_tenant(tenants, checked.append)

    check()
    tenants.ids = (ANNA, BRUNO)
    check()

    assert checked == [ANNA, ANNA, BRUNO]


def test_nothing_runs_before_the_check() -> None:
    checked = list[TenantId]()

    every_tenant(Tenants(), checked.append)

    assert checked == []
