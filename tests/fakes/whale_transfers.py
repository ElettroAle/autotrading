"""Fake of the port of the large transfers: a provider of on-chain transfers named by the test (R5.1.1)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_parameter import SourceParameter
from autotrading.domain.sources.whale import MINIMUM_USD
from autotrading.domain.sources.whale_transfer import WhaleTransfer

API_KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)
THRESHOLD = SourceParameter(MINIMUM_USD, "soglia USD", default=1_000_000, minimum=100_000, maximum=1_000_000_000)


@dataclass(frozen=True, slots=True)
class TransfersAsked:
    """One reading the provider received: the window, the threshold and the credentials of the tenant."""

    since: datetime
    until: datetime
    minimum_usd: int
    credentials: Mapping[str, str]


@dataclass
class FakeWhaleTransfersAdapter:
    """A provider that answers, as the real one, the transfers the test publishes within the window and at or above the
    threshold asked; it may be out of reach, refuse the credentials, or ignore the threshold and answer every
    transfer of the window."""

    name: str
    published: list[WhaleTransfer] = field(default_factory=list)
    reachable: bool = True
    rejects_credentials: bool = False
    ignores_threshold: bool = False
    asked: list[TransfersAsked] = field(default_factory=list)

    def declaration(self) -> SourceAdapterDeclaration:
        return SourceAdapterDeclaration(
            self.name, f"grandi trasferimenti di {self.name}", (THRESHOLD,), (API_KEY,), offers_history=True
        )

    def transfers(
        self, since: datetime, until: datetime, minimum_usd: int, credentials: Mapping[str, str]
    ) -> Sequence[WhaleTransfer]:
        self.asked.append(TransfersAsked(since, until, minimum_usd, dict(credentials)))
        if not self.reachable:
            raise SourceUnavailableError(self.name)
        if self.rejects_credentials:
            raise SourceCredentialsRejectedError(self.name)
        return [
            transfer
            for transfer in self.published
            if since <= transfer.at <= until and (self.ignores_threshold or transfer.usd_value >= minimum_usd)
        ]
