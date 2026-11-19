from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import NotRequired, TypedDict, cast

import httpx

from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.errors import InvalidWhaleTransferError
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_parameter import SourceParameter
from autotrading.domain.sources.whale import MINIMUM_USD
from autotrading.domain.sources.whale_transfer import WhaleTransfer

TIMEOUT_SECONDS = 10.0
ARKHAM_URL = "https://api.arkm.com"
TRANSFERS_PATH = "/transfers"
# The Intel API reads the key from this header only, never from Authorization (https://intel.arkm.com/llms/guides/
# api-keys-authentication.md).
KEY_HEADER = "API-Key"
# The largest transfers of the interval first: the agent reads at most this many of them.
LIMIT = 100
REFUSED_CODES = frozenset({401, 403})
API_KEY = SourceConfigurationField("api_key", "chiave API", secret=True)
THRESHOLD = SourceParameter(MINIMUM_USD, "soglia USD", default=1_000_000, minimum=100_000, maximum=1_000_000_000)
# An adapter of the whale source (R5.1.1): the endpoint filters by instant, so it offers historical data too.
DECLARATION = SourceAdapterDeclaration(
    "Arkham",
    "Grandi trasferimenti on-chain dall'API Intel di Arkham, con entità ed etichette di origine e destinazione; "
    "richiede una chiave API gratuita.",
    (THRESHOLD,),
    (API_KEY,),
    offers_history=True,
)


class _ArkhamName(TypedDict):
    name: NotRequired[str]


class _ArkhamAddress(TypedDict):
    arkhamEntity: NotRequired[_ArkhamName | None]
    arkhamLabel: NotRequired[_ArkhamName | None]


class _ArkhamTransfer(TypedDict):
    blockTimestamp: str
    tokenSymbol: str
    unitValue: float
    historicalUSD: float
    fromAddress: _ArkhamAddress
    toAddress: _ArkhamAddress


class _ArkhamTransfers(TypedDict):
    transfers: NotRequired[list[_ArkhamTransfer]]


class ArkhamWhaleTransfersAdapter:
    """The large transfers of the Intel API of Arkham, read with the key of the tenant (R5.1.1, ADR
    fonte-whale-con-adapter-arkham)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def declaration(self) -> SourceAdapterDeclaration:
        return DECLARATION

    def transfers(
        self, since: datetime, until: datetime, minimum_usd: int, credentials: Mapping[str, str]
    ) -> Sequence[WhaleTransfer]:
        document = self._document(_query(since, until, minimum_usd), credentials.get(API_KEY.name, ""))
        try:
            return [_transfer_of(entry) for entry in cast("_ArkhamTransfers", document).get("transfers", [])]
        except (AttributeError, KeyError, TypeError, ValueError, InvalidOperation, InvalidWhaleTransferError) as error:
            raise SourceUnavailableError(DECLARATION.name) from error

    def _document(self, query: Mapping[str, str], key: str) -> object:
        try:
            response = self._client.get(
                TRANSFERS_PATH, params=query, headers={KEY_HEADER: key}, timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            # Any other shape fails on the first lookup, inside the adapter that reads it.
            document: object = response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code in REFUSED_CODES:
                raise SourceCredentialsRejectedError(DECLARATION.name) from error
            raise SourceUnavailableError(DECLARATION.name) from error
        except (httpx.HTTPError, ValueError) as error:
            raise SourceUnavailableError(DECLARATION.name) from error
        return document


def _query(since: datetime, until: datetime, minimum_usd: int) -> dict[str, str]:
    return {
        "timeGte": _milliseconds(since),
        "timeLte": _milliseconds(until),
        "usdGte": str(minimum_usd),
        "sortKey": "usd",
        "sortDir": "desc",
        "limit": str(LIMIT),
    }


def _milliseconds(instant: datetime) -> str:
    return str(int(instant.timestamp() * 1000))


def _transfer_of(entry: _ArkhamTransfer) -> WhaleTransfer:
    return WhaleTransfer(
        datetime.fromisoformat(entry["blockTimestamp"]),
        entry["tokenSymbol"],
        Decimal(str(entry["unitValue"])),
        Decimal(str(entry["historicalUSD"])),
        _described(entry["fromAddress"]),
        _described(entry["toAddress"]),
    )


def _described(address: _ArkhamAddress) -> str | None:
    """The entity that owns the address and the label of the address, as Arkham attributes them, when known."""
    entity = _name_of(address.get("arkhamEntity"))
    label = _name_of(address.get("arkhamLabel"))
    if entity and label:
        return f"{entity} ({label})"
    return entity or label or None


def _name_of(named: _ArkhamName | None) -> str | None:
    return None if named is None else named.get("name")
