from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.risk_check import AssetLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection


@dataclass(frozen=True, slots=True)
class FlowAccount:
    """What a flow needs of its account: the exchange it trades on and the balance read from it now."""

    exchange: str
    balance: Decimal
    currency: str


class FlowRepositoryPort(Protocol):
    """Bound to the tenant of the request: it never sees the flows of another tenant."""

    def list(self) -> list[Flow]:
        """Every flow of the tenant with the configuration version in force."""
        ...

    def name_in_use(self, name: FlowName) -> bool:
        """True when a flow of the tenant not archived has the name."""
        ...

    def add(self, flow: Flow) -> None:
        """Saves the flow with its first configuration version.

        Raises FlowNameInUseError, or FlowAccountNotFoundError when the account is not of the tenant any more.
        """
        ...

    def get(self, flow_id: FlowId) -> Flow:
        """The flow with the configuration version in force. Raises FlowNotFoundError."""
        ...

    def version(self, flow_id: FlowId, number: int) -> FlowConfiguration:
        """One configuration version of the flow. Raises FlowNotFoundError or FlowVersionNotFoundError."""
        ...

    def change_status(self, flow: Flow) -> None:
        """Saves the status of the flow. Raises FlowNotFoundError."""
        ...

    def add_version(self, flow: Flow) -> None:
        """Saves the configuration of the flow as a new version, the others untouched. Raises FlowNotFoundError."""
        ...


class FlowAccountPort(Protocol):
    """Bound to the tenant of the request."""

    def account(self, account_id: UUID) -> FlowAccount:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the balance cannot be read."""
        ...


class MarketsPort(Protocol):
    def tradable_assets(self) -> frozenset[str]:
        """The assets the exchange trades now. Raises FlowExchangeUnavailableError."""
        ...


class ModelSettingsPort(Protocol):
    """Bound to the tenant of the request: a model is usable only with the key of its provider (R1.4.1)."""

    def selection(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        """The model with its parameters resolved. Raises InvalidFlowSettingError with the reason."""
        ...


class SourceSettingsPort(Protocol):
    def selection(self, source: str, weight: int | None, requested: Mapping[str, int]) -> SourceSelection:
        """The source with its parameters resolved. Raises InvalidFlowSettingError with the reason."""
        ...


class ExchangeLimitsPort(Protocol):
    """What the exchange of the account of the flow accepts on an asset, read now (R1.5.2, R1.5.4)."""

    def limits(self, asset: str) -> AssetLimits | None:
        """None when the exchange does not trade the asset. Raises FlowExchangeUnavailableError."""
        ...
