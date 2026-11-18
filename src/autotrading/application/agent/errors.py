from collections.abc import Iterable, Mapping
from decimal import Decimal

from autotrading.application.errors import ApplicationError
from autotrading.domain.agent.model_usage import ModelPrices, ModelSpend, ModelUsage
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.errors import ErrorScope


class UnsupportedProviderError(ApplicationError):
    status_code = 422

    def __init__(self, provider: ProviderName, supported: Iterable[ProviderName]) -> None:
        super().__init__(f"fornitore non supportato: {provider.value}")
        self.provider = provider
        self.supported = tuple(sorted(name.value for name in supported))

    @property
    def details(self) -> Mapping[str, object]:
        return {"supported": list(self.supported)}


class ProviderKeyAlreadyRegisteredError(ApplicationError):
    status_code = 409

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"chiave già registrata per il fornitore: {provider.value}")
        self.provider = provider


class ProviderKeyNotFoundError(ApplicationError):
    status_code = 404

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"nessuna chiave registrata per il fornitore: {provider.value}")
        self.provider = provider


class ProviderKeyInUseError(ApplicationError):
    status_code = 409

    def __init__(self, flows: Iterable[str]) -> None:
        self.flows = tuple(sorted(flows))
        super().__init__("chiave usata da flussi attivi o in pausa: " + ", ".join(self.flows))


class ModelKeyRejectedError(ApplicationError):
    """The provider refuses the key during a cycle: it repeats at every cycle until the user acts (R1.2.4)."""

    status_code = 422
    declared_permanent = True

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"chiave del fornitore non valida: {provider.value}")
        self.provider = provider

    @property
    def scope(self) -> ErrorScope:
        return ErrorScope(provider=self.provider.value)


class ModelCreditExhaustedError(ApplicationError):
    """The account of the user at the provider has no credit left: it repeats until the user tops it up (R1.2.4)."""

    status_code = 402
    declared_permanent = True

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"credito esaurito presso {provider.value}")
        self.provider = provider

    @property
    def scope(self) -> ErrorScope:
        return ErrorScope(provider=self.provider.value)


class ModelUnavailableError(ApplicationError):
    """The provider did not answer, or answered with an error that may not repeat: only the cycle fails (R1.2.3).

    A call that went out may have been charged: the error says so, with the usage the provider reported when it did,
    so the cycle still records the call (R1.4.6, ADR uso-riportato-nell-errore-della-chiamata-al-modello), and with
    how many calls the question tried, one until it is asked again (R1.4.9, ADR
    tentativi-del-modello-registrati-nel-ciclo).
    """

    status_code = 503

    def __init__(  # noqa: PLR0913 - the provider and its message, then what the calls spent, each by name
        self,
        provider: ProviderName,
        original: str,
        *,
        usage: ModelUsage | None = None,
        sent: bool = False,
        cost_usd: Decimal | None = None,
        attempts: int = 1,
    ) -> None:
        super().__init__(f"fornitore IA non raggiungibile: {provider.value}: {original}")
        self.provider = provider
        self.original = original
        self.usage = usage
        self.sent = sent
        self.cost_usd = cost_usd
        self.attempts = attempts

    def priced(self, prices: ModelPrices | None) -> ModelUnavailableError:
        """The same error with the cost of the reported usage, priced as every answered call is (R1.4.6)."""
        cost = None if self.usage is None else self.usage.cost_usd(prices)
        return ModelUnavailableError(
            self.provider, self.original, usage=self.usage, sent=self.sent, cost_usd=cost, attempts=self.attempts
        )

    def spent_after(self, spend: ModelSpend) -> ModelSpend:
        """What the calls before this one spent, with this call when it went out; tried, it is an attempt anyway
        (R1.4.6, R1.4.9).
        """
        if not self.sent:
            return spend.with_attempt()
        return spend.with_call(self.usage, self.cost_usd)

    def with_spend(self, spend: ModelSpend) -> ModelUnavailableError:
        """The same error carrying what every call of the question consumed and how many it tried, the retried ones
        included (R1.4.6, R1.4.9, ADR tentativi-del-modello-registrati-nel-ciclo).
        """
        return ModelUnavailableError(
            self.provider,
            self.original,
            usage=spend.usage,
            sent=spend.sent,
            cost_usd=spend.cost_usd,
            attempts=spend.attempts,
        )


class ModelKeyMissingError(ApplicationError):
    """A flow runs on a provider the tenant has no key for: it repeats until the user registers one (R1.2.4)."""

    status_code = 422
    declared_permanent = True

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"nessuna chiave registrata per il fornitore: {provider.value}")
        self.provider = provider

    @property
    def scope(self) -> ErrorScope:
        return ErrorScope(provider=self.provider.value)


class ProviderKeyNotOpenedError(ApplicationError):
    """The worker cannot open a sealed key: it repeats until the user registers the key again (ADR 0029)."""

    status_code = 500
    declared_permanent = True

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"chiave del fornitore non leggibile: {provider.value}")
        self.provider = provider

    @property
    def scope(self) -> ErrorScope:
        return ErrorScope(provider=self.provider.value)


class ModelCatalogUnavailableError(ApplicationError):
    """The model gateway does not tell which models it offers right now: nothing is chosen or called (ADR 0103)."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("catalogo dei modelli non disponibile")
