from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId


def test_a_tenant_is_founded_for_its_owner_with_a_new_identifier() -> None:
    owner = UserId("oid-anna")

    first, second = Tenant.found_for(owner), Tenant.found_for(owner)

    assert first.owner == owner
    assert first.id != second.id
