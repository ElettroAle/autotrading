from uuid import UUID

from autotrading.domain.tenancy.tenant_id import TenantId


def test_new_identifiers_are_distinct_uuids() -> None:
    first, second = TenantId.new(), TenantId.new()

    assert isinstance(first.value, UUID)
    assert first != second


def test_identifier_is_rebuilt_from_its_text() -> None:
    identifier = TenantId.new()

    assert TenantId.parse(str(identifier.value)) == identifier
