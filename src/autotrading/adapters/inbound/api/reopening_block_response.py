from datetime import datetime

from pydantic import BaseModel

from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.trade_side import TradeSide


class ReopeningBlockResponse(BaseModel):
    """The openings on a side stopped after consecutive losses until an instant: on the asset, or on every asset of the
    flow when the asset is null, with the text the dashboard shows (R5.5.2).
    """

    side: TradeSide
    asset: str | None
    consecutive_losses: int
    until: datetime
    text: str

    @classmethod
    def of(cls, block: ReopeningBlock) -> ReopeningBlockResponse:
        return cls(
            side=block.side,
            asset=block.asset,
            consecutive_losses=block.consecutive_losses,
            until=block.until,
            text=block.state_text,
        )
