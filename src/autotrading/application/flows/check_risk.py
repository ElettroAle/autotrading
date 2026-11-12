from dataclasses import dataclass

from autotrading.application.flows.ports import ExchangeLimitsPort
from autotrading.domain.flows.risk_check import RiskCheck, RiskPolicy, RiskState
from autotrading.domain.flows.risk_outcome import BlockedDecision, RiskOutcome
from autotrading.domain.flows.trade_intent import OpenIntent, TradeIntent


@dataclass(frozen=True, slots=True)
class CheckRiskCommand:
    """The decisions of a cycle, with the risk policy and the state of the flow read at the start of the cycle."""

    intents: tuple[TradeIntent, ...]
    policy: RiskPolicy
    state: RiskState


class CheckRiskUseCase:
    """Turns each decision of the agent into an approved order, a blocked decision or a hold (R1.5.1-R1.5.4).

    A blocked decision never stops the others of the cycle; an approved opening commits its margin, so the next
    decisions see only the liquidity left (ADR 0065).
    """

    def __init__(self, exchange_limits: ExchangeLimitsPort) -> None:
        self._exchange_limits = exchange_limits

    def execute(self, command: CheckRiskCommand) -> tuple[RiskOutcome, ...]:
        check = RiskCheck(command.policy, command.state)
        return tuple(self._outcome(check, intent) for intent in command.intents)

    def _outcome(self, check: RiskCheck, intent: TradeIntent) -> RiskOutcome:
        if not isinstance(intent, OpenIntent):
            return check.outcome(intent, None)
        limits = self._exchange_limits.limits(intent.asset)
        if limits is None:
            return BlockedDecision(intent.asset, f"asset non negoziabile sull'exchange: {intent.asset}")
        return check.outcome(intent, limits)
