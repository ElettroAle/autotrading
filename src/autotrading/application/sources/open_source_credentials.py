from collections.abc import Mapping
from types import MappingProxyType

from autotrading.application.sources.ports import SourceCredentialsRepositoryPort, SourceSecretsOpenerPort
from autotrading.domain.sources.errors import SourceAdapterNotConfiguredError
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration


class OpenSourceCredentialsUseCase:
    """The values an adapter reads its provider with, in the worker: the public ones and the secret ones opened, none
    for an adapter that declares no field (R4.1.2, ADR credenziali-degli-adapter-delle-fonti).

    Credentials missing at the moment of the cycle make the adapter absent with the reason (R1.2.5).
    """

    def __init__(self, credentials: SourceCredentialsRepositoryPort, opener: SourceSecretsOpenerPort) -> None:
        self._credentials = credentials
        self._opener = opener

    def execute(self, adapter: SourceAdapterDeclaration) -> Mapping[str, str]:
        if not adapter.needs_configuration:
            return MappingProxyType({})
        saved = self._credentials.get(adapter.name)
        if saved is None:
            raise SourceAdapterNotConfiguredError(adapter.name)
        return MappingProxyType({**saved.public_values, **self._opener.open(saved)})
