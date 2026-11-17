from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.agent.errors import InvalidModelUsageError

MILLION = Decimal(1_000_000)


@dataclass(frozen=True, slots=True)
class ModelPrices:
    """The price of a model in USD per million tokens, from the catalog (R1.4.6)."""

    input_per_million: Decimal
    output_per_million: Decimal

    def __post_init__(self) -> None:
        if self.input_per_million < 0 or self.output_per_million < 0:
            raise InvalidModelUsageError


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """What one call to the model consumed, as the provider reported it (R1.4.6)."""

    input_tokens: int
    output_tokens: int
    reported_cost_usd: Decimal | None

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise InvalidModelUsageError
        if self.reported_cost_usd is not None and self.reported_cost_usd < 0:
            raise InvalidModelUsageError

    def cost_usd(self, prices: ModelPrices | None) -> Decimal | None:
        """The cost the provider reported, otherwise the one the catalog prices give, otherwise not available."""
        if self.reported_cost_usd is not None:
            return self.reported_cost_usd
        if prices is None:
            return None
        return (self.input_tokens * prices.input_per_million + self.output_tokens * prices.output_per_million) / MILLION

    def plus(self, other: ModelUsage | None) -> ModelUsage:
        """This usage and the other together; the reported cost is known only when both report it."""
        if other is None:
            return self
        return ModelUsage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            _sum(self.reported_cost_usd, other.reported_cost_usd),
        )


@dataclass(frozen=True, slots=True)
class ModelSpend:
    """What the calls of one question to the model consumed together, the retried ones included (R1.4.6, ADR
    ritentativo-del-modello-nel-ciclo).

    The usage adds up what the provider reported; the cost is not available as soon as one call that went out has none.
    Nothing is spent until a call goes out.
    """

    usage: ModelUsage | None = None
    cost_usd: Decimal | None = None
    sent: bool = False

    def with_call(self, usage: ModelUsage | None, cost_usd: Decimal | None) -> ModelSpend:
        """A call that went out, with its usage when the provider reported it and its cost when somebody knows it."""
        reported = self.usage if usage is None else usage.plus(self.usage)
        return ModelSpend(reported, self._cost_with(cost_usd), sent=True)

    def _cost_with(self, cost_usd: Decimal | None) -> Decimal | None:
        if not self.sent:
            return cost_usd
        return _sum(self.cost_usd, cost_usd)


def _sum(first: Decimal | None, second: Decimal | None) -> Decimal | None:
    if first is None or second is None:
        return None
    return first + second
