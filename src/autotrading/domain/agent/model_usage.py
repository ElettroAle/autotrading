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
