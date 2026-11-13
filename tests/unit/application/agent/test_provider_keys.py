from decimal import Decimal

import pytest

from autotrading.application.agent.errors import (
    ProviderKeyAlreadyRegisteredError,
    ProviderKeyInUseError,
    ProviderKeyNotFoundError,
    ProviderRejectedKeyError,
    ProviderUnavailableError,
    UnsupportedProviderError,
)
from autotrading.application.agent.list_models import ListModelsUseCase, ProviderListing
from autotrading.application.agent.list_provider_keys import ListProviderKeysUseCase
from autotrading.application.agent.ports import ModelUse
from autotrading.application.agent.register_provider_key import (
    ProviderKeyServices,
    RegisterProviderKeyCommand,
    RegisterProviderKeyUseCase,
)
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyCommand, RemoveProviderKeyUseCase
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyCommand, ReplaceProviderKeyUseCase
from autotrading.domain.agent.errors import ProviderKeyRequiredError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import RangeParameter
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.provider_keys import (
    FakeProviderKeySealerAdapter,
    FakeProviderKeyUsageAdapter,
    FakeProviderKeyVerifierAdapter,
    InMemoryProviderKeyRepositoryAdapter,
    ProviderKeyStore,
    ProviderKeyVault,
)

OPENROUTER = ProviderName("openrouter")
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
        self.verifier = FakeProviderKeyVerifierAdapter()
        self.usage = FakeProviderKeyUsageAdapter()
        self.services = ProviderKeyServices(
            CATALOG, self.verifier, FakeProviderKeySealerAdapter(self.tenant_id, self.vault)
        )

    def register(self, provider: str, key: str) -> ProviderName:
        use_case = RegisterProviderKeyUseCase(self.tenant_id, self.repository, self.services)
        return use_case.execute(RegisterProviderKeyCommand(provider, key))

    def replace(self, provider: str, key: str) -> ProviderName:
        return ReplaceProviderKeyUseCase(self.repository, self.services).execute(
            ReplaceProviderKeyCommand(provider, key)
        )

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


def test_a_key_the_provider_accepts_is_saved_sealed_for_the_tenant(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")

    assert keys.register(" OpenRouter ", "K-OR") == OPENROUTER

    (registered,) = keys.store.keys
    assert (registered.tenant_id, registered.provider) == (keys.tenant_id, OPENROUTER)
    assert b"K-OR" not in registered.sealed.ciphertext
    assert keys.opened_key_of(OPENROUTER) == ProviderKey("K-OR")


def test_a_key_the_provider_refuses_is_not_saved(keys: Keys) -> None:
    with pytest.raises(ProviderRejectedKeyError, match=r"^chiave rifiutata dal fornitore: openrouter$"):
        keys.register("openrouter", "K-BAD")

    assert keys.store.keys == []


def test_a_provider_out_of_reach_saves_nothing(keys: Keys) -> None:
    keys.verifier.unreachable.add(OPENROUTER)

    with pytest.raises(ProviderUnavailableError) as raised:
        keys.register("openrouter", "K-OR")

    assert raised.value.status_code == 503
    assert keys.store.keys == []


def test_a_provider_outside_the_catalog_is_refused_before_asking_it(keys: Keys) -> None:
    with pytest.raises(UnsupportedProviderError, match=r"^fornitore non supportato: openai$") as raised:
        keys.register("openai", "K-OA")

    assert raised.value.details == {"supported": ["anthropic", "openrouter"]}
    assert keys.verifier.checked == []


def test_an_empty_key_is_refused_before_asking_the_provider(keys: Keys) -> None:
    with pytest.raises(ProviderKeyRequiredError):
        keys.register("openrouter", "  ")

    assert keys.verifier.checked == []


def test_a_second_key_for_the_same_provider_is_refused_before_asking_it(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")
    keys.verifier.accept("openrouter", "K-OR2")
    keys.register("openrouter", "K-OR")

    with pytest.raises(
        ProviderKeyAlreadyRegisteredError, match=r"^chiave già registrata per il fornitore: openrouter$"
    ):
        keys.register("openrouter", "K-OR2")

    assert keys.verifier.checked == [OPENROUTER]
    assert keys.opened_key_of(OPENROUTER) == ProviderKey("K-OR")


def test_the_replacement_puts_the_new_accepted_key_in_place(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")
    keys.verifier.accept("openrouter", "K-OR2")
    keys.register("openrouter", "K-OR")

    assert keys.replace("openrouter", "K-OR2") == OPENROUTER

    assert len(keys.store.keys) == 1
    assert keys.opened_key_of(OPENROUTER) == ProviderKey("K-OR2")


def test_a_refused_replacement_keeps_the_old_key(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")
    keys.register("openrouter", "K-OR")

    with pytest.raises(ProviderRejectedKeyError):
        keys.replace("openrouter", "K-BAD")

    assert keys.opened_key_of(OPENROUTER) == ProviderKey("K-OR")


def test_a_replacement_without_a_registered_key_is_refused(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")

    with pytest.raises(ProviderKeyNotFoundError, match=r"^nessuna chiave registrata per il fornitore: openrouter$"):
        keys.replace("openrouter", "K-OR")

    assert keys.verifier.checked == []


def test_the_removal_deletes_the_key(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")
    keys.register("openrouter", "K-OR")

    keys.remove("OpenRouter")

    assert keys.store.keys == []


def test_the_removal_is_refused_while_flows_that_are_not_stopped_use_the_provider(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")
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
    keys.verifier.accept("openrouter", "K-OR")
    keys.register("openrouter", "K-OR")
    keys.usage.uses = [ModelUse("fermo", "openrouter", running=False), ModelUse("altro", "anthropic", running=True)]

    keys.remove("openrouter")

    assert keys.store.keys == []


def test_the_removal_of_a_key_never_registered_is_refused(keys: Keys) -> None:
    with pytest.raises(ProviderKeyNotFoundError):
        keys.remove("openrouter")


def test_the_list_names_the_providers_and_never_the_keys(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")
    keys.verifier.accept("anthropic", "K-AN")
    keys.register("openrouter", "K-OR")
    keys.register("anthropic", "K-AN")

    assert ListProviderKeysUseCase(keys.repository).execute() == [ProviderName("anthropic"), OPENROUTER]


def test_the_catalog_says_for_each_provider_whether_the_tenant_has_its_key(keys: Keys) -> None:
    keys.verifier.accept("openrouter", "K-OR")
    keys.register("openrouter", "K-OR")

    listing = ListModelsUseCase(CATALOG, keys.repository).execute()

    assert listing.models == CATALOG.models
    assert listing.providers == (
        ProviderListing(ProviderName("anthropic"), key_registered=False),
        ProviderListing(OPENROUTER, key_registered=True),
    )


def test_the_commands_never_show_the_key() -> None:
    for command in (
        RegisterProviderKeyCommand("openrouter", "K-SECRET"),
        ReplaceProviderKeyCommand("openrouter", "K-SECRET"),
    ):
        assert "K-SECRET" not in repr(command)
