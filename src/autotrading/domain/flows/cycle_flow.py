from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.cycle_funds import CycleFunds
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_state_view import FlowStateView, PositionView
from autotrading.domain.flows.risk_check import RiskState
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class CycleFlow:
    """The flow of a cycle as read at its start: whose it is, its configuration in force, its state now.

    The amounts are the state attributed to the flow, the same the user consults (R1.6.1, ADR 0062); the account
    gives only the details of the positions and the margin it has free, which no flow may go beyond.
    """

    tenant_id: TenantId
    flow: Flow
    account_name: str
    exchange: str
    started_at: datetime
    account: CycleAccount
    attributed: FlowState

    @property
    def configuration(self) -> FlowConfiguration:
        return self.flow.configuration

    @property
    def positions(self) -> tuple[CyclePosition, ...]:
        return self.configuration.held(self.account.positions, lambda position: position.asset)

    @property
    def available_liquidity(self) -> Decimal:
        return self._funds.available_liquidity

    @property
    def total_value(self) -> Decimal:
        return self._funds.total_value

    @property
    def return_percent(self) -> Decimal:
        return self._funds.return_percent

    @property
    def _funds(self) -> CycleFunds:
        return CycleFunds(self.attributed, self.account.available_margin)

    def risk_state(self) -> RiskState:
        return RiskState(
            currency=self.account.currency,
            funds=self.attributed.funds,
            available_liquidity=self.available_liquidity,
            open_assets=frozenset(position.asset for position in self.positions),
        )

    @property
    def sources(self) -> tuple[str, ...]:
        """The active sources of the configuration in force at the start: a change waits for the next cycle."""
        return tuple(source.name for source in self.configuration.sources)

    def state_view(self) -> FlowStateView:
        """The state of the flow alone, as the agent and the record of the cycle see it (R1.4.3)."""
        return FlowStateView(
            currency=self.account.currency,
            allocated_capital=self.configuration.assigned_capital,
            funds=self.attributed.funds,
            available_liquidity=self.available_liquidity,
            total_value=self.total_value,
            return_percent=self.return_percent,
            positions=tuple(
                PositionView(
                    position.asset,
                    position.side,
                    position.size,
                    position.leverage,
                    position.entry_price,
                    position.unrealized_pnl,
                    position.liquidation_price,
                )
                for position in self.positions
            ),
        )
