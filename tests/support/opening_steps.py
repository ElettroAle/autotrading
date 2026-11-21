"""The register of the openings of the credentials of an account and of the keys of the AI providers, read as the
threat model reads it (Bug 179).

The fake openers of the platform write it as the opener of the worker does; the lines libsodium writes are proven by
its unit tests.
"""

from pytest_bdd import given, then

from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.credential_sealer import KEY_VERSION as CREDENTIALS_KEY_VERSION
from tests.fakes.provider_keys import KEY_VERSION as PROVIDER_KEY_VERSION
from tests.support.flow_cycles import KEY, FlowCycles
from tests.support.openings import Opening
from tests.support.platform import Platform
from tests.support.steps import quoted

OUTCOMES = {"riuscita": True, "rifiutata": False}


def assert_recorded(platform: Platform, opening: Opening, tenant_id: TenantId, outcome: str, key_version: int) -> None:
    assert opening.opened is OUTCOMES[outcome], opening
    assert opening.tenant_id == tenant_id
    assert opening.key_version == key_version
    assert opening.at == platform.worker_clock.current


def credential_openings(platform: Platform, account: str) -> list[Opening]:
    recorded = platform.openings.of(f"conto {platform.account_named('anna', account).id.value}")
    assert recorded, "no opening of the credentials was recorded"
    return recorded


def key_openings(platform: Platform, provider: str) -> list[Opening]:
    recorded = platform.openings.of(f"chiave {provider}")
    assert recorded, "no opening of the key was recorded"
    return recorded


@given(quoted('che le credenziali salvate del conto "{account}" non si possono più aprire'))
def credentials_no_longer_open(platform: Platform, account: str) -> None:
    # The private key of the worker no longer recovers what the API sealed.
    del platform.vault[platform.account_named("anna", account).credentials.ciphertext]


@then(
    quoted(
        'l\'apertura delle credenziali del conto "{account}" è registrata con il tenant, la versione della chiave, '
        "l'esito \"{outcome}\" e l'istante"
    )
)
def last_opening_recorded(platform: Platform, account: str, outcome: str) -> None:
    saved = platform.account_named("anna", account)
    opening = credential_openings(platform, account)[-1]
    assert_recorded(platform, opening, saved.tenant_id, outcome, CREDENTIALS_KEY_VERSION)


@then(
    quoted(
        'ogni apertura delle credenziali del conto "{account}" è registrata con il tenant, la versione della chiave, '
        "l'esito \"{outcome}\" e l'istante"
    )
)
def every_opening_recorded(platform: Platform, account: str, outcome: str) -> None:
    saved = platform.account_named("anna", account)
    for opening in credential_openings(platform, account):
        assert_recorded(platform, opening, saved.tenant_id, outcome, CREDENTIALS_KEY_VERSION)


@then(quoted('la registrazione non contiene le credenziali del conto "{account}"'))
def register_without_credentials(platform: Platform, account: str) -> None:
    texts = [repr(opening).lower() for opening in credential_openings(platform, account)]
    secrets = [value.lower() for credentials in platform.issued for value in credentials.values.values()]
    assert secrets, "no credentials were issued"
    assert not [secret for secret in secrets if any(secret in text for text in texts)]


@given(quoted('che la chiave salvata del fornitore "{provider}" non si può più aprire'))
def provider_key_no_longer_opens(flow_cycles: FlowCycles, provider: str) -> None:
    (key,) = [key for key in flow_cycles.platform.provider_keys.keys if key.provider.value == provider]
    # The private key of the worker no longer recovers what the API sealed.
    del flow_cycles.platform.key_vault[key.sealed.ciphertext]


@then(
    quoted(
        'l\'apertura della chiave del fornitore "{provider}" è registrata con il tenant, la versione della chiave, '
        "l'esito \"{outcome}\" e l'istante"
    )
)
def key_opening_recorded(flow_cycles: FlowCycles, provider: str, outcome: str) -> None:
    opening = key_openings(flow_cycles.platform, provider)[-1]
    tenant_id = flow_cycles.flow("alfa").tenant_id
    assert_recorded(flow_cycles.platform, opening, tenant_id, outcome, PROVIDER_KEY_VERSION)


@then(quoted('la registrazione non contiene la chiave del fornitore "{provider}"'))
def register_without_key(flow_cycles: FlowCycles, provider: str) -> None:
    texts = [repr(opening) for opening in key_openings(flow_cycles.platform, provider)]
    assert not [text for text in texts if KEY in text]
