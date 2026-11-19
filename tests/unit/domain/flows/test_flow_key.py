from datetime import date
from uuid import uuid4

from autotrading.domain.flows.flow_key import FlowKey
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import ANTHROPIC_MODEL, OPENROUTER_MODEL, a_configuration, a_flow

ACCOUNT = uuid4()


def test_a_key_is_expired_from_the_day_of_its_expiry() -> None:
    key = FlowKey("openrouter", date(2026, 12, 15), provider="openrouter")

    assert [key.is_expired_on(day) for day in (date(2026, 12, 14), date(2026, 12, 15), date(2026, 12, 16))] == [
        False,
        True,
        True,
    ]
    assert key.pause_reason == "chiave openrouter scaduta"


def test_the_credentials_serve_the_flows_of_the_account_and_a_provider_key_the_flows_of_its_models() -> None:
    tenant = TenantId.new()
    on_account = a_flow(tenant, account_id=ACCOUNT, configuration=a_configuration(model=ANTHROPIC_MODEL))
    on_openrouter = a_flow(tenant, account_id=uuid4(), configuration=a_configuration(model=OPENROUTER_MODEL))
    credentials = FlowKey("test-1", date(2026, 12, 15), account_id=ACCOUNT)
    provider_key = FlowKey("openrouter", date(2026, 12, 15), provider="openrouter")

    assert (credentials.used_by(on_account), credentials.used_by(on_openrouter)) == (True, False)
    assert (provider_key.used_by(on_account), provider_key.used_by(on_openrouter)) == (False, True)
