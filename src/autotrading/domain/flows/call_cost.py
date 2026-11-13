from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.errors import InvalidCallCostError


@dataclass(frozen=True, slots=True)
class CallCost:
    """Tokens and cost in USD of the model call of a cycle; the cost is None when neither side knows it (R1.4.6)."""

    input_tokens: int
    output_tokens: int
    cost_usd: Decimal | None

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise InvalidCallCostError
        if self.cost_usd is not None and self.cost_usd < 0:
            raise InvalidCallCostError
