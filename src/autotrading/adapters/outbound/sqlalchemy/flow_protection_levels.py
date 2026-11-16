from collections.abc import Iterable

from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.protection_repository import protection_of
from autotrading.adapters.outbound.sqlalchemy.tables import flow_protections
from autotrading.domain.flows.exit_plan import PlacedLevels
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyFlowProtectionLevelsAdapter:
    """The levels of the protections in force of the flows of one tenant, read from those the platform recorded, under
    row level security (R3.1.3, ADR aggiornamento-del-piano-di-uscita-di-una-posizione-aperta).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def placed_levels(self, flow_id: FlowId, asset: str) -> PlacedLevels:
        query = select(flow_protections).where(
            flow_protections.c.flow_id == flow_id.value,
            flow_protections.c.asset == asset,
            flow_protections.c.removed_at.is_(None),
        )
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            rows = connection.execute(query).mappings().all()
        return levels_of(protection_of(row) for row in rows)


def levels_of(protections: Iterable[PlacedProtection]) -> PlacedLevels:
    prices = {protection.kind: protection.trigger_price for protection in protections}
    return PlacedLevels(prices.get(ProtectionKind.STOP_LOSS), prices.get(ProtectionKind.TAKE_PROFIT))
