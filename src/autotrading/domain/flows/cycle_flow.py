from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.cycle_funds import CycleFunds
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_state_view import FlowStateView, PositionView
from autotrading.domain.flows.openings_suspension import OpeningsSuspension
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.risk_check import RiskState
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class CycleFlow:
    """The flow of a cycle as read at its start: whose it is, its configuration in force, its state now.

    The amounts are the state attributed to the flow, the same the user consults (R1.6.1, ADR 0062); the account
    gives only the details of the positions and the margin it has free, which no flow may go beyond. An alarm of
    reconciliation open on the account suspends the openings of the flow (R3.3.1).
    """

    tenant_id: TenantId
    flow: Flow
    account_name: str
    exchange: str
    started_at: datetime
    account: CycleAccount
    attributed: FlowState
    alarm: ReconciliationAlarm | None = None

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
    def return_percent(self) -> Decimal | None:
        return self._funds.return_percent

    @property
    def _funds(self) -> CycleFunds:
        return CycleFunds(self.attributed, self.account.available_margin)

    def risk_state(self, *, loss_suspension: OpeningsSuspension | None = None) -> RiskState:
        """The margin of the open positions is the one the exchange declares, as in the liquidity (ADR 0067); their
        value is at the mark price (R3.2.1). The openings are suspended by what the guard of the losses found (R3.2.2)
        or by an alarm of reconciliation on the account (R3.3.1).
        """
        attributed = self.attributed
        suspension = self.openings_suspension(loss_suspension)
        return RiskState(
            currency=self.account.currency,
            funds=attributed.funds,
            available_liquidity=self.available_liquidity,
            open_positions=frozendict({position.asset: position.side for position in self.positions}),
            open_margin=attributed.margin,
            open_value=sum((position.size * position.mark_price for position in attributed.positions), Decimal(0)),
            openings_suspended=None if suspension is None else suspension.blocked_reason,
        )

    def openings_suspension(self, loss_suspension: OpeningsSuspension | None) -> OpeningsSuspension | None:
        alarm_suspension = None if self.alarm is None else self.alarm.suspension(self.account_name)
        return OpeningsSuspension.first_of(loss_suspension, alarm_suspension)

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
                    position.mark_price,
                    position.unrealized_pnl,
                    position.liquidation_price,
                    self.attributed.exit_plan_of(position.asset),
                )
                for position in self.positions
            ),
        )
