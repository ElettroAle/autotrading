from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from autotrading.domain.agent.agent_context import ModelMessage
from autotrading.domain.agent.answer_format import AnswerFormat
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey


class ProviderKeySealerPort(Protocol):
    """Bound to the tenant of the request: the sealed text names tenant and provider (ADR 0029)."""

    def seal(self, provider: ProviderName, key: ProviderKey) -> SealedProviderKey: ...


class ProviderKeyOpenerPort(Protocol):
    """In the worker only: the private key of the installation never reaches the API (ADR 0007, ADR 0029)."""

    def open(self, key: RegisteredProviderKey) -> ProviderKey:
        """Raises ProviderKeyNotOpenedError when the sealed text is not of the tenant and provider of the key."""
        ...


@dataclass(frozen=True, slots=True)
class ProviderKeyRegistration:
    """A provider the tenant has a key for, and the instant of its last registration or replacement (ADR 0130)."""

    provider: ProviderName
    registered_at: datetime


class ProviderKeyRepositoryPort(Protocol):
    """Bound to the tenant of the request: it never sees the keys of another tenant."""

    def list(self) -> list[RegisteredProviderKey]: ...

    def registrations(self) -> tuple[ProviderKeyRegistration, ...]:
        """The providers of the keys of the tenant, by name, each with the instant its key was saved."""
        ...

    def get(self, provider: ProviderName) -> RegisteredProviderKey | None: ...

    def add(self, key: RegisteredProviderKey) -> ProviderKeyRegistration:
        """Raises ProviderKeyAlreadyRegisteredError when the tenant already has a key for that provider."""
        ...

    def replace(self, key: RegisteredProviderKey) -> ProviderKeyRegistration:
        """Raises ProviderKeyNotFoundError when the tenant has no key for that provider."""
        ...

    def remove(self, provider: ProviderName) -> None:
        """Raises ProviderKeyNotFoundError when the tenant has no key for that provider."""
        ...


@dataclass(frozen=True, slots=True)
class ModelUse:
    """A flow of the tenant and the provider of its model; a running flow is one not stopped (ADR 0087)."""

    flow_name: str
    provider: str
    running: bool


class ProviderKeyUsagePort(Protocol):
    """Bound to the tenant of the request."""

    def model_uses(self) -> tuple[ModelUse, ...]:
        """Every flow of the tenant with the provider of its model."""
        ...


@dataclass(frozen=True, slots=True)
class ModelReply:
    """The text the model answered with, and what the call consumed (R1.4.4, R1.4.6)."""

    text: str
    usage: ModelUsage


class ModelCatalogPort(Protocol):
    """The models the platform offers now, with their parameters and prices, from the model gateway (R1.4.2)."""

    def catalog(self) -> ModelCatalog:
        """Raises ModelCatalogUnavailableError."""
        ...


class ModelCallPort(Protocol):
    """Calls a model of the catalog with the key of the user, from the worker only (ADR 0007).

    The model is asked to answer in the given format, enforced by the provider where the model supports it (ADR
    risposta-del-modello-con-schema-rigido).
    """

    def call(
        self,
        model: str,
        key: ProviderKey,
        settings: Mapping[str, ParameterValue],
        messages: tuple[ModelMessage, ...],
        answer: AnswerFormat,
    ) -> ModelReply:
        """Raises ModelKeyRejectedError or ModelCreditExhaustedError (permanent), or ModelUnavailableError."""
        ...


class PausePort(Protocol):
    """Waits before the use case asks the model again in the same cycle (ADR ritentativo-del-modello-nel-ciclo)."""

    def pause(self, seconds: float) -> None: ...


class ModelGatewayPort(Protocol):
    """Abstract factory of one model gateway: the call and the catalog of the same models, one family (ADR 0109).

    Each gateway serves the models of its own catalog; the use case uses the one whose catalog holds the model the
    flow chose.
    """

    def model_call(self) -> ModelCallPort: ...

    def model_catalog(self) -> ModelCatalogPort: ...


class QuestionExitPlanPort(Protocol):
    """The exit plan in force of an open position of the flow, as the cycle of the flow hands it (R3.1.1)."""

    @property
    def target(self) -> Decimal | None: ...

    @property
    def stop(self) -> Decimal | None: ...

    @property
    def invalidation(self) -> str | None: ...


class QuestionPositionPort(Protocol):
    """An open position of the flow, as the cycle of the flow hands it to the agent."""

    @property
    def asset(self) -> str: ...

    @property
    def direction(self) -> str: ...

    @property
    def size(self) -> Decimal: ...

    @property
    def leverage(self) -> int: ...

    @property
    def entry_price(self) -> Decimal: ...

    @property
    def mark_price(self) -> Decimal: ...

    @property
    def unrealized_pnl(self) -> Decimal: ...

    @property
    def liquidation_price(self) -> Decimal | None: ...

    @property
    def exit_plan(self) -> QuestionExitPlanPort: ...


class QuestionStatePort(Protocol):
    """The state of the flow alone, as the cycle of the flow hands it to the agent (R1.4.3)."""

    @property
    def currency(self) -> str: ...

    @property
    def allocated_capital(self) -> Decimal: ...

    @property
    def funds(self) -> Decimal: ...

    @property
    def available_liquidity(self) -> Decimal: ...

    @property
    def total_value(self) -> Decimal: ...

    @property
    def return_percent(self) -> Decimal | None: ...

    @property
    def positions(self) -> Sequence[QuestionPositionPort]: ...


class QuestionSourcePort(Protocol):
    """The values of one active source in the cycle, with its weight (R1.3.2)."""

    @property
    def source(self) -> str: ...

    @property
    def weight(self) -> int: ...

    @property
    def asset(self) -> str | None: ...

    @property
    def values(self) -> Mapping[str, str]: ...


class AgentQuestionPort(Protocol):
    """What the cycle of a flow asks the agent: the model of the flow and everything the agent receives (R1.4.3)."""

    @property
    def model(self) -> str: ...

    @property
    def settings(self) -> Mapping[str, ParameterValue]: ...

    @property
    def system_prompt(self) -> str:
        """The system message of the flow, already rendered with its values (R1.4.8)."""
        ...

    @property
    def assets(self) -> Sequence[str]: ...

    @property
    def started_at(self) -> datetime: ...

    @property
    def now(self) -> datetime: ...

    @property
    def state(self) -> QuestionStatePort: ...

    @property
    def sources(self) -> Sequence[QuestionSourcePort]: ...

    @property
    def missing(self) -> Sequence[str]: ...
