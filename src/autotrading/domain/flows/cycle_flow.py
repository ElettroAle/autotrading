from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.account_exposure_reading import AccountExposureReading
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.cycle_funds import CycleFunds
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_state_view import FlowStateView, PositionView
from autotrading.domain.flows.openings_suspension import OpeningsSuspension
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.risk_check import RiskState
from autotrading.domain.flows.selections import ActiveSource
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class CycleFlow:
    """The flow of a cycle as read at its start: whose it is, its configuration in force, its state now.

    The amounts are the state attributed to the flow, the same the user consults (R1.6.1, ADR 0062); the account
    gives only the details of the positions and the margin it has free, which no flow may go beyond. An alarm of
    reconciliation open on the account suspends the openings of the flow (R3.3.1). The exposure of the account is what
    the cycle read of it, for its limit and for the agent (R5.5.5).
    """

    tenant_id: TenantId
    flow: Flow
    account_name: str
    exchange: str
    started_at: datetime
    account: CycleAccount
    attributed: FlowState
    alarm: ReconciliationAlarm | None = None
    account_exposure: AccountExposureReading = field(default_factory=AccountExposureReading)

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
        or by an alarm of reconciliation on the account (R3.3.1), and blocked on a side after consecutive losses
        (R5.5.2) or beyond the limit of the account (R5.5.5).
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
            trailing_stops=frozendict(self._trailing_stops()),
            reopening_blocks=attributed.reopening_blocks,
            account_exposure=self.account_exposure.of_account,
            account_exposure_limit=self.account_exposure.limit,
        )

    def _trailing_stops(self) -> dict[str, Decimal]:
        """The stop the platform computes for each open position whose stop follows the price, from the best price it
        reached and the price of now; none before the activation (R5.5.1, ADR
        sorveglianza-del-prezzo-per-lo-stop-che-segue).
        """
        trailing = self.configuration.trailing_stop
        if not trailing.active:
            return {}
        stops = {position.asset: self._trailing_stop_of(trailing, position) for position in self.positions}
        return {asset: stop for asset, stop in stops.items() if stop is not None}

    def _trailing_stop_of(self, trailing: TrailingStop, position: CyclePosition) -> Decimal | None:
        watched = self.attributed.watched.get(position.asset)
        previous = None if watched is None else watched.best_price
        best = TrailingStop.best_price(position.side, previous, position.mark_price)
        return trailing.stop_of(position.side, position.entry_price, best)

    def _max_profit_for_agent(self, asset: str) -> Decimal | None:
        """Only with the option on does the agent see the largest profit the position reached (ADR
        massimo-profitto-raggiunto-nello-stato-della-posizione)."""
        if not self.configuration.trailing_stop.max_profit_for_agent:
            return None
        return self.attributed.max_profit_of(asset)

    def openings_suspension(self, loss_suspension: OpeningsSuspension | None) -> OpeningsSuspension | None:
        alarm_suspension = None if self.alarm is None else self.alarm.suspension(self.account_name)
        return OpeningsSuspension.first_of(loss_suspension, alarm_suspension)

    @property
    def sources(self) -> tuple[ActiveSource, ...]:
        """The adapters of the active sources of the configuration in force at the start: a change waits for the next
        cycle (R4.1.1).
        """
        return self.configuration.active_sources

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
                    self._max_profit_for_agent(position.asset),
                )
                for position in self.positions
            ),
            reopening_blocks=tuple(block.state_text for block in self.attributed.reopening_blocks),
            account_exposure=self._others_exposure_text(),
        )

    def _others_exposure_text(self) -> str | None:
        """Only with the option on does the agent see the exposure of the other flows of the account (ADR
        esposizione-degli-altri-flussi-nel-contesto-dell-agente)."""
        others = self.account_exposure.of_others
        return None if others is None else others.others_text(self.account.currency)
