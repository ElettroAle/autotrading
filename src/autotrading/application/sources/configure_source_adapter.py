import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.sources.ports import SourceCredentialsRepositoryPort, SourceSecretsSealerPort
from autotrading.domain.sources.key_expiry import KeyExpiry
from autotrading.domain.sources.source_credentials import SourceConfigurationValues, SourceCredentials
from autotrading.domain.tenancy.tenant_id import TenantId

operations = logging.getLogger("autotrading.sources")


@dataclass(frozen=True, slots=True)
class ConfigureSourceAdapterCommand:
    adapter: str
    values: Mapping[str, str] = field(repr=False)
    # The day the credentials stop working, when the user knows it (R6.2.2).
    expires_on: date | None = None


class ConfigureSourceAdapterUseCase:
    """Saves once for all the flows of the tenant the credentials of an adapter of a source, or puts new ones in place
    of the saved ones: the values of the fields the adapter declares, the secrets sealed (R4.1.2, ADR
    credenziali-degli-adapter-delle-fonti).

    New credentials are not refused yet, and carry only the expiry given with them (R6.2.2).
    """

    def __init__(
        self,
        tenant_id: TenantId,
        sources: ListSourcesUseCase,
        credentials: SourceCredentialsRepositoryPort,
        sealer: SourceSecretsSealerPort,
    ) -> None:
        self._tenant_id = tenant_id
        self._sources = sources
        self._credentials = credentials
        self._sealer = sealer

    def execute(self, command: ConfigureSourceAdapterCommand) -> None:
        adapter = self._sources.execute().configurable_adapter(command.adapter)
        values = SourceConfigurationValues.declared(adapter.declaration.configuration_fields, command.values)
        sealed = self._sealer.seal(adapter.name, values.secrets)
        expiry = None if command.expires_on is None else KeyExpiry.entered(command.expires_on)
        self._credentials.save(SourceCredentials(self._tenant_id, adapter.name, values.public, sealed, expiry))
        operations.info("credenziali dell'adapter della fonte salvate", extra={"adapter": adapter.name})
