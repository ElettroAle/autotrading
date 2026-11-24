from uuid import uuid4

from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.tenancy.tenant_id import TenantId


def test_an_account_without_credentials_has_nothing_to_open() -> None:
    tenant_id = TenantId.new()

    assert not SealedAccess(tenant_id, uuid4(), "simulato", 0, b"").has_credentials
    assert SealedAccess(tenant_id, uuid4(), "Hyperliquid", 1, b"sealed").has_credentials
