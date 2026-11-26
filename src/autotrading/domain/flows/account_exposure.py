from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.cycle_account import CyclePosition
from autotrading.domain.flows.risk_limits import HUNDRED
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.italian_text import money_text, number_text

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class AccountExposure:
    """The value, size by market price, of the positions the flows of an account hold on each side (R5.5.5).

    The two sides never offset each other. Only the positions on the assets of the flows counted count: one no flow
    explains does not.
    """

    long: Decimal = ZERO
    short: Decimal = ZERO

    @classmethod
    def of(cls, positions: Iterable[CyclePosition], assets: Collection[str]) -> AccountExposure:
        """The positions of the account on the assets of the flows counted."""
        held = [position for position in positions if position.asset in assets]
        return cls(_value_on(held, TradeSide.LONG), _value_on(held, TradeSide.SHORT))

    def on(self, side: TradeSide) -> Decimal:
        return self.long if side is TradeSide.LONG else self.short

    def adding(self, side: TradeSide, value: Decimal) -> AccountExposure:
        """The exposure once an opening of that value on that side is approved."""
        if side is TradeSide.LONG:
            return AccountExposure(self.long + value, self.short)
        return AccountExposure(self.long, self.short + value)

    def others_text(self, currency: str) -> str:
        """The line of the state the agent receives, when the exposure is that of the other flows of the account (ADR
        esposizione-degli-altri-flussi-nel-contesto-dell-agente)."""
        return (
            f"altri flussi del conto: long {money_text(self.long)} {currency}, "
            f"short {money_text(self.short)} {currency}"
        )


def _value_on(positions: Sequence[CyclePosition], side: TradeSide) -> Decimal:
    return sum((position.size * position.mark_price for position in positions if position.side is side), ZERO)


@dataclass(frozen=True, slots=True)
class AccountExposureLimit:
    """The largest exposure the flows of an account may have together on one side: a percent of its balance read from
    the exchange, in its currency (R5.5.5, ADR controllo-dell-esposizione-del-conto-nel-rischio).

    An exposure exactly at the limit is within it.
    """

    percent: Decimal
    balance: Decimal
    currency: str

    @property
    def amount(self) -> Decimal:
        return self.balance * self.percent / HUNDRED

    def exceeded_by(self, exposure: Decimal) -> bool:
        return exposure > self.amount

    def opening_reason(self, side: TradeSide, asset: str, exposure: Decimal) -> str:
        """Why an opening that would bring the exposure of its side to that amount is blocked."""
        return (
            f"apertura {side} su {asset} bloccata: esposizione {side} del conto {self._money(exposure)} "
            f"oltre il limite di {self._money(self.amount)} "
            f"({number_text(self.percent)}% del saldo {self._money(self.balance)})"
        )

    def _money(self, amount: Decimal) -> str:
        return f"{money_text(amount)} {self.currency}"
