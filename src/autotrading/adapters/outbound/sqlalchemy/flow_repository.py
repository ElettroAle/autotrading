from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from decimal import Decimal
from typing import NotRequired, TypedDict, cast
from uuid import UUID

from sqlalchemy import Connection, Engine, RowMapping, Select, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import flow_capital_changes, flow_versions, flows
from autotrading.application.agent.ports import ModelUse
from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowNameInUseError,
    FlowNotFoundError,
    FlowVersionNotFoundError,
)
from autotrading.application.flows.ports import FlowVersion
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow import Flow, holder_of
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelParameterValue, ModelSelection, SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

NAME_UNIQUE_IN_TENANT = "flows_name_unique_in_tenant"
ACCOUNT_OF_TENANT = "flows_account_of_tenant"
NOT_ARCHIVED = flows.c.status != FlowStatus.ARCHIVED.name.lower()


class _ModelDocument(TypedDict):
    name: str
    parameters: dict[str, dict[str, str]]


class _SourceDocument(TypedDict):
    name: str
    weight: int
    parameters: dict[str, int]


class _RiskLimitsDocument(TypedDict):
    max_leverage: int
    max_margin_exposure_percent: str | None
    max_value_exposure_percent: str | None


class _ConfigurationDocument(TypedDict):
    """A configuration version as saved in JSON; a wrong shape fails while it is read."""

    assets: list[str]
    cycle_minutes: int
    model: _ModelDocument
    sources: list[_SourceDocument]
    instructions: str
    risk_limits: _RiskLimitsDocument
    allocated_capital: str
    bring_to_minimum: NotRequired[bool]


class SqlAlchemyFlowRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def flow_on(self, account_id: UUID, asset: str) -> str | None:
        """The flow the verification procedure keeps off the asset of the account (ADR 0075)."""
        return holder_of(self.list(), account_id, asset)

    def list(self) -> list[Flow]:
        with self._transaction() as connection:
            return [_flow_of(row) for row in connection.execute(_in_force().order_by(flows.c.name)).mappings()]

    def exists(self, flow_id: UUID) -> bool:
        """For the cycles (ADR 0046): the flow belongs to the tenant of the request."""
        return any(flow.id.value == flow_id for flow in self.list())

    def model_uses(self) -> tuple[ModelUse, ...]:
        """For the agent (R1.4.1, ADR 0087): every flow with the provider of its model and whether it runs."""
        return tuple(ModelUse(flow.name.value, flow.model_provider, flow.status.not_stopped) for flow in self.list())

    def get(self, flow_id: FlowId) -> Flow:
        with self._transaction() as connection:
            row = connection.execute(_in_force().where(flows.c.id == flow_id.value)).mappings().one_or_none()
        if row is None:
            raise FlowNotFoundError
        return _flow_of(row)

    def version(self, flow_id: FlowId, number: int) -> FlowConfiguration:
        query = select(flow_versions.c.configuration).where(
            flow_versions.c.flow_id == flow_id.value, flow_versions.c.version == number
        )
        self.get(flow_id)
        with self._transaction() as connection:
            document = connection.execute(query).scalar_one_or_none()
        if document is None:
            raise FlowVersionNotFoundError(number)
        return configuration_of(number, document)

    def versions(self, flow_id: FlowId) -> tuple[FlowVersion, ...]:
        query = (
            select(flow_versions.c.version, flow_versions.c.created_at)
            .where(flow_versions.c.flow_id == flow_id.value)
            .order_by(flow_versions.c.version.desc())
        )
        self.get(flow_id)
        with self._transaction() as connection:
            rows = connection.execute(query).all()
        return tuple(FlowVersion(number, created_at) for number, created_at in rows)

    def change_status(self, flow: Flow) -> None:
        statement = update(flows).where(flows.c.id == flow.id.value).values(status=flow.status.name.lower())
        with self._transaction() as connection:
            changed = connection.execute(statement).rowcount
        if not changed:
            raise FlowNotFoundError

    def add_version(self, flow: Flow) -> None:
        if flow.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self.get(flow.id)
        with self._transaction() as connection:
            connection.execute(insert(flow_versions).values(_version_row_of(flow)))

    def add_capital_change(self, flow: Flow, change: CapitalChange) -> None:
        if flow.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self.get(flow.id)
        with self._transaction() as connection:
            connection.execute(insert(flow_versions).values(_version_row_of(flow)))
            connection.execute(
                insert(flow_capital_changes).values(
                    flow_id=flow.id.value,
                    tenant_id=flow.tenant_id.value,
                    changed_at=change.changed_at,
                    previous_capital=change.previous,
                    new_capital=change.new,
                    user_id=change.user_id.value,
                    version=flow.configuration.version,
                )
            )

    def capital_changes(self, flow_id: FlowId) -> tuple[CapitalChange, ...]:
        query = (
            select(flow_capital_changes)
            .where(flow_capital_changes.c.flow_id == flow_id.value)
            .order_by(flow_capital_changes.c.changed_at, flow_capital_changes.c.id)
        )
        self.get(flow_id)
        with self._transaction() as connection:
            rows = connection.execute(query).mappings().all()
        return tuple(
            CapitalChange(
                flow_id,
                row["changed_at"],
                Decimal(row["previous_capital"]),
                Decimal(row["new_capital"]),
                UserId(row["user_id"]),
            )
            for row in rows
        )

    def name_in_use(self, name: FlowName) -> bool:
        query = select(func.count()).select_from(flows).where(NOT_ARCHIVED, flows.c.name == name.value)
        with self._transaction() as connection:
            return bool(connection.execute(query).scalar_one())

    def add(self, flow: Flow) -> None:
        if flow.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        try:
            with self._transaction() as connection:
                connection.execute(insert(flows).values(_row_of(flow)))
                connection.execute(insert(flow_versions).values(_version_row_of(flow)))
        except IntegrityError as error:
            if NAME_UNIQUE_IN_TENANT in str(error.orig):
                raise FlowNameInUseError from error
            # The account was removed after the use case read it: the flow has no account to run on.
            if ACCOUNT_OF_TENANT in str(error.orig):
                raise FlowAccountNotFoundError from error
            raise

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _in_force() -> Select[tuple[object, ...]]:
    """Every flow with its configuration version in force: the highest number it has."""
    current = (
        select(flow_versions.c.flow_id, func.max(flow_versions.c.version).label("version"))
        .group_by(flow_versions.c.flow_id)
        .subquery()
    )
    return (
        select(flows, flow_versions.c.version, flow_versions.c.configuration)
        .join(current, current.c.flow_id == flows.c.id)
        .join(
            flow_versions,
            (flow_versions.c.flow_id == current.c.flow_id) & (flow_versions.c.version == current.c.version),
        )
    )


def _row_of(flow: Flow) -> dict[str, object]:
    return {
        "id": flow.id.value,
        "tenant_id": flow.tenant_id.value,
        "account_id": flow.account_id,
        "name": flow.name.value,
        "status": flow.status.name.lower(),
    }


def _version_row_of(flow: Flow) -> dict[str, object]:
    return {
        "flow_id": flow.id.value,
        "tenant_id": flow.tenant_id.value,
        "version": flow.configuration.version,
        "configuration": document_of(flow.configuration),
    }


def document_of(configuration: FlowConfiguration) -> dict[str, object]:
    """The configuration as JSON: amounts and parameters as text, so no number is rounded."""
    limits = configuration.risk_limits
    return {
        "assets": list(configuration.assets),
        "cycle_minutes": configuration.cycle_interval.minutes,
        "model": {"name": configuration.model.name, "parameters": _texts(configuration.model.parameters)},
        "sources": [
            {"name": source.name, "weight": source.weight, "parameters": dict(source.parameters)}
            for source in configuration.sources
        ],
        "instructions": configuration.instructions,
        "risk_limits": {
            "max_leverage": limits.max_leverage,
            "max_margin_exposure_percent": _text(limits.max_margin_exposure_percent),
            "max_value_exposure_percent": _text(limits.max_value_exposure_percent),
        },
        "allocated_capital": str(configuration.allocated_capital),
        "bring_to_minimum": configuration.bring_to_minimum,
    }


def configuration_of(version: int, saved: Mapping[str, object]) -> FlowConfiguration:
    document = cast("_ConfigurationDocument", saved)
    limits = document["risk_limits"]
    model = document["model"]
    return FlowConfiguration(
        version=version,
        assets=tuple(document["assets"]),
        cycle_interval=CycleInterval(document["cycle_minutes"]),
        model=ModelSelection(model["name"], {key: _parameter(value) for key, value in model["parameters"].items()}),
        sources=tuple(
            SourceSelection(source["name"], source["weight"], dict(source["parameters"]))
            for source in document["sources"]
        ),
        instructions=document["instructions"],
        risk_limits=RiskLimits(
            limits["max_leverage"],
            _decimal(limits["max_margin_exposure_percent"]),
            _decimal(limits["max_value_exposure_percent"]),
        ),
        allocated_capital=Decimal(document["allocated_capital"]),
        # Versions saved before the option existed read with it off, its default (ADR 0051).
        bring_to_minimum=document.get("bring_to_minimum", False),
    )


def _flow_of(row: RowMapping) -> Flow:
    return Flow(
        FlowId(row["id"]),
        TenantId(row["tenant_id"]),
        row["account_id"],
        FlowName(row["name"]),
        FlowStatus[row["status"].upper()],
        configuration_of(row["version"], row["configuration"]),
    )


def _texts(parameters: Mapping[str, ModelParameterValue]) -> dict[str, dict[str, str]]:
    # The kind is kept, so a number written as text never comes back as a choice.
    return {
        key: {"number": str(value)} if isinstance(value, Decimal) else {"choice": value}
        for key, value in parameters.items()
    }


def _parameter(value: Mapping[str, str]) -> ModelParameterValue:
    return Decimal(value["number"]) if "number" in value else value["choice"]


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)
