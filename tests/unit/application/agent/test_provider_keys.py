from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from autotrading.application.agent.errors import (
    KeyExpiryReadByAdapterError,
    ProviderKeyAlreadyRegisteredError,
    ProviderKeyInUseError,
    ProviderKeyNotFoundError,
    UnsupportedProviderError,
)
from autotrading.application.agent.list_models import ListModelsUseCase, ProviderListing
from autotrading.application.agent.list_provider_keys import ListProviderKeysUseCase
from autotrading.application.agent.ports import ModelUse, ProviderKeyRegistration
from autotrading.application.agent.provider_key_summary import ProviderKeySummary
from autotrading.application.agent.register_provider_key import (
    ProviderKeyServices,
    RegisterProviderKeyCommand,
    RegisterProviderKeyUseCase,
)
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyCommand, RemoveProviderKeyUseCase
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyCommand, ReplaceProviderKeyUseCase
from autotrading.domain.agent.errors import ProviderKeyRequiredError
from autotrading.domain.agent.key_expiry import KeyExpiry, KeyExpiryStatus
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import RangeParameter
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_key_field import API_KEY_FIELD
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.provider_keys import (
    FakeProviderKeySealerAdapter,
    FakeProviderKeyUsageAdapter,
    InMemoryProviderKeyRepositoryAdapter,
    ProviderKeyStore,
    ProviderKeyVault,
)
from tests.support.provider_key import api_key_of, key_values

OPENROUTER = ProviderName("openrouter")
TODAY = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
CATALOG = ModelCatalog(
    (
        ModelDefinition(
            "openrouter/deepseek-chat", (RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1)),)
        ),
        ModelDefinition("anthropic/claude-sonnet", ()),
    )
)


class Keys:
    """One tenant with the fakes of every port the use cases on keys run on."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = ProviderKeyStore()
        self.vault: ProviderKeyVault = {}
        self.repository = InMemoryProviderKeyRepositoryAdapter(self.store, self.tenant_id)
        self.usage = FakeProviderKeyUsageAdapter()
        self.services = ProviderKeyServices(
            {"models": InMemoryModelCatalogAdapter(CATALOG)},
            FakeProviderKeySealerAdapter(self.tenant_id, self.vault),
        )

    def register(self, provider: str, key: str, expires_on: date | None = None) -> ProviderKeyRegistration:
        use_case = RegisterProviderKeyUseCase(self.tenant_id, self.repository, self.services)
        return use_case.execute(RegisterProviderKeyCommand(provider, key_values(key), expires_on))

    def replace(self, provider: str, key: str, expires_on: date | None = None) -> ProviderKeyRegistration:
        return ReplaceProviderKeyUseCase(self.repository, self.services).execute(
            ReplaceProviderKeyCommand(provider, key_values(key), expires_on)
        )

    def listed(self) -> list[ProviderKeySummary]:
        return ListProviderKeysUseCase(self.repository, self.services.catalogs, lambda: TODAY).execute()

    def remove(self, provider: str) -> None:
        RemoveProviderKeyUseCase(self.repository, self.usage).execute(RemoveProviderKeyCommand(provider))

    def opened_key_of(self, provider: ProviderName) -> ProviderKey:
        registered = self.repository.get(provider)
        assert registered is not None
        tenant_id, sealed_provider, key = self.vault[registered.sealed.ciphertext]
        assert (tenant_id, sealed_provider) == (self.tenant_id, provider)
        return key


@pytest.fixture
def keys() -> Keys:
    return Keys()


def test_a_key_is_saved_sealed_for_the_tenant_without_asking_the_provider(keys: Keys) -> None:

    assert keys.register(" OpenRouter ", "K-OR").provider == OPENROUTER

    (registered,) = keys.store.keys
    assert (registered.tenant_id, registered.provider) == (keys.tenant_id, OPENROUTER)
    assert b"K-OR" not in registered.sealed.ciphertext
    assert keys.opened_key_of(OPENROUTER) == api_key_of("K-OR")


def test_a_provider_outside_the_catalog_is_refused(keys: Keys) -> None:
    with pytest.raises(UnsupportedProviderError, match=r"^fornitore non supportato: openai$") as raised:
        keys.register("openai", "K-OA")

    assert raised.value.details == {"supported": ["anthropic", "openrouter"]}


def test_an_empty_key_is_refused(keys: Keys) -> None:
    with pytest.raises(ProviderKeyRequiredError):
        keys.register("openrouter", "  ")


def test_a_second_key_for_the_same_provider_is_refused(keys: Keys) -> None:
    keys.register("openrouter", "K-OR")

    with pytest.raises(
        ProviderKeyAlreadyRegisteredError, match=r"^chiave già registrata per il fornitore: openrouter$"
    ):
        keys.register("openrouter", "K-OR2")

    assert keys.opened_key_of(OPENROUTER) == api_key_of("K-OR")


def test_the_replacement_puts_the_new_key_in_place(keys: Keys) -> None:
    keys.register("openrouter", "K-OR")

    assert keys.replace("openrouter", "K-OR2").provider == OPENROUTER

    assert len(keys.store.keys) == 1
    assert keys.opened_key_of(OPENROUTER) == api_key_of("K-OR2")


def test_a_replacement_without_a_registered_key_is_refused(keys: Keys) -> None:

    with pytest.raises(ProviderKeyNotFoundError, match=r"^nessuna chiave registrata per il fornitore: openrouter$"):
        keys.replace("openrouter", "K-OR")


def test_the_removal_deletes_the_key(keys: Keys) -> None:
    keys.register("openrouter", "K-OR")

    keys.remove("OpenRouter")

    assert keys.store.keys == []


def test_the_removal_is_refused_while_flows_that_are_not_stopped_use_the_provider(keys: Keys) -> None:
    keys.register("openrouter", "K-OR")
    keys.usage.uses = [
        ModelUse("beta", "openrouter", running=True),
        ModelUse("fermo", "openrouter", running=False),
        ModelUse("altro", "anthropic", running=True),
        ModelUse("alfa", "openrouter", running=True),
    ]

    with pytest.raises(ProviderKeyInUseError, match=r"^chiave usata da flussi attivi o in pausa: alfa, beta$"):
        keys.remove("openrouter")

    assert len(keys.store.keys) == 1


def test_flows_stopped_or_on_another_provider_leave_the_key_removable(keys: Keys) -> None:
    keys.register("openrouter", "K-OR")
    keys.usage.uses = [ModelUse("fermo", "openrouter", running=False), ModelUse("altro", "anthropic", running=True)]

    keys.remove("openrouter")

    assert keys.store.keys == []


def test_the_removal_of_a_key_never_registered_is_refused(keys: Keys) -> None:
    with pytest.raises(ProviderKeyNotFoundError):
        keys.remove("openrouter")


def test_the_list_names_the_providers_with_the_instant_of_registration_and_never_the_keys(keys: Keys) -> None:
    openrouter = keys.register("openrouter", "K-OR")
    anthropic = keys.register("anthropic", "K-AN")

    listed = keys.listed()

    assert [(key.provider, key.registered_at) for key in listed] == [
        (anthropic.provider, anthropic.registered_at),
        (openrouter.provider, openrouter.registered_at),
    ]
    assert (anthropic.provider, openrouter.provider) == (ProviderName("anthropic"), OPENROUTER)


def test_the_registration_answers_with_the_instant_the_key_was_saved(keys: Keys) -> None:
    keys.store.now = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)

    registration = keys.register("openrouter", "K-OR")

    assert registration == ProviderKeyRegistration(OPENROUTER, datetime(2026, 11, 14, 9, 30, tzinfo=UTC))


def test_the_replacement_answers_with_the_instant_of_the_new_key(keys: Keys) -> None:
    keys.store.now = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)
    keys.register("openrouter", "K-OR")
    keys.store.now = datetime(2026, 11, 14, 10, 7, tzinfo=UTC)

    replacement = keys.replace("openrouter", "K-OR2")

    assert replacement.registered_at == datetime(2026, 11, 14, 10, 7, tzinfo=UTC)
    assert [(key.provider, key.registered_at) for key in keys.listed()] == [
        (replacement.provider, replacement.registered_at)
    ]


def test_the_catalog_says_for_each_provider_whether_the_tenant_has_its_key(keys: Keys) -> None:
    keys.register("openrouter", "K-OR")

    listing = ListModelsUseCase({"models": InMemoryModelCatalogAdapter(CATALOG)}, keys.repository).execute()

    assert listing.models == CATALOG.models
    assert listing.providers == (
        ProviderListing(
            ProviderName("anthropic"), key_registered=False, key_fields=(API_KEY_FIELD,), expiry_editable=True
        ),
        ProviderListing(OPENROUTER, key_registered=True, key_fields=(API_KEY_FIELD,), expiry_editable=True),
    )


def test_the_commands_never_show_the_key() -> None:
    for command in (
        RegisterProviderKeyCommand("openrouter", key_values("K-SECRET")),
        ReplaceProviderKeyCommand("openrouter", key_values("K-SECRET")),
    ):
        assert "K-SECRET" not in repr(command)


def test_a_key_is_registered_with_the_expiry_the_user_gives(keys: Keys) -> None:
    registration = keys.register("openrouter", "K-OR", date(2026, 12, 15))

    assert registration.expiry == KeyExpiry.entered(date(2026, 12, 15))
    [listed] = keys.listed()
    assert (listed.reading.status, listed.reading.days_left, listed.expiry_editable) == (
        KeyExpiryStatus.EXPIRING,
        26,
        True,
    )


def test_a_key_registered_without_a_date_has_an_unknown_expiry(keys: Keys) -> None:
    keys.register("openrouter", "K-OR")

    [listed] = keys.listed()
    assert (listed.expiry, listed.reading.status) == (None, KeyExpiryStatus.UNKNOWN)


def test_the_replacement_forgets_the_expiry_of_the_old_key_and_keeps_the_one_given_with_the_new(keys: Keys) -> None:
    keys.register("openrouter", "K-OR", date(2026, 11, 24))

    assert keys.replace("openrouter", "K-OR2").expiry is None
    assert keys.replace("openrouter", "K-OR3", date(2027, 3, 15)).expiry == KeyExpiry.entered(date(2027, 3, 15))


def test_a_date_is_refused_for_a_provider_whose_gateway_reads_the_expiry(keys: Keys) -> None:
    keys.services = ProviderKeyServices(
        {"models": InMemoryModelCatalogAdapter(CATALOG, reading_expiry=frozenset({"openrouter"}))},
        keys.services.sealer,
    )

    with pytest.raises(KeyExpiryReadByAdapterError):
        keys.register("openrouter", "K-OR", date(2026, 12, 15))

    assert keys.store.keys == []
    keys.register("openrouter", "K-OR")
    assert not keys.listed()[0].expiry_editable


def test_the_catalog_says_for_each_provider_whether_the_user_gives_the_expiry_of_its_key(keys: Keys) -> None:
    """R6.2.2: the registration asks the expiry only where no gateway reads it."""
    catalog = InMemoryModelCatalogAdapter(CATALOG, reading_expiry=frozenset({"anthropic"}))

    listing = ListModelsUseCase({"models": catalog}, keys.repository).execute()

    assert [(listed.provider.value, listed.expiry_editable) for listed in listing.providers] == [
        ("anthropic", False),
        ("openrouter", True),
    ]
