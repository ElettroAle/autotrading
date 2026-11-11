from collections.abc import Iterable, Mapping

from autotrading.application.errors import ApplicationError
from autotrading.domain.agent.provider_name import ProviderName


class UnsupportedProviderError(ApplicationError):
    status_code = 422

    def __init__(self, provider: ProviderName, supported: Iterable[ProviderName]) -> None:
        super().__init__(f"fornitore non supportato: {provider.value}")
        self.provider = provider
        self.supported = tuple(sorted(name.value for name in supported))

    @property
    def details(self) -> Mapping[str, object]:
        return {"supported": list(self.supported)}


class ProviderRejectedKeyError(ApplicationError):
    status_code = 422

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"chiave rifiutata dal fornitore: {provider.value}")
        self.provider = provider


class ProviderUnavailableError(ApplicationError):
    status_code = 503

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"fornitore non raggiungibile, riprovare: {provider.value}")
        self.provider = provider


class ProviderNotVerifiableError(ApplicationError):
    """A provider of the catalog without a way to verify its keys: a defect of the configuration (ADR 0029)."""

    status_code = 500

    def __init__(self, provider: ProviderName) -> None:
        super().__init__(f"verifica della chiave non disponibile per il fornitore: {provider.value}")
        self.provider = provider


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
