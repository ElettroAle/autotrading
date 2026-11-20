"""The cache of the readings of an account, composed once for the API process (ADR
cache-delle-letture-del-conto-come-decorator-in-memoria)."""

from uuid import uuid4

from autotrading.adapters.outbound.process_memory.account_activity import ProcessMemoryAccountActivityAdapter
from autotrading.adapters.outbound.process_memory.composition import process_memory_adapters
from autotrading.adapters.outbound.process_memory.configuration import _ProcessMemorySettings
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter


def test_a_reading_of_the_account_stays_valid_ten_seconds_by_default() -> None:
    assert _ProcessMemorySettings().account_activity_validity_seconds == 10.0


def test_the_composition_decorates_the_port_for_the_tenant_of_the_request() -> None:
    remember = process_memory_adapters()

    decorated = remember(FakeAccountActivityAdapter(), TenantId.new())

    assert isinstance(decorated, ProcessMemoryAccountActivityAdapter)


def test_the_requests_of_one_composition_share_one_store() -> None:
    remember, worker = process_memory_adapters(), FakeAccountActivityAdapter()
    tenant_id, account_id = TenantId.new(), uuid4()

    remember(worker, tenant_id).execute(account_id)
    remember(worker, tenant_id).execute(account_id)

    assert worker.read == [account_id]


def test_every_composition_has_its_own_store() -> None:
    worker, tenant_id, account_id = FakeAccountActivityAdapter(), TenantId.new(), uuid4()

    process_memory_adapters()(worker, tenant_id).execute(account_id)
    process_memory_adapters()(worker, tenant_id).execute(account_id)

    assert worker.read == [account_id, account_id]
