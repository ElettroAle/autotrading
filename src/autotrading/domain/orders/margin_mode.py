from __future__ import annotations

from enum import StrEnum


class MarginMode(StrEnum):
    """How the exchange guarantees a position: with its own margin, or with the balance of the whole account."""

    ISOLATED = "isolated"
    CROSS = "cross"

    @classmethod
    def per_position(cls) -> MarginMode:
        # Several flows may share an account: an isolated position loses at most its own margin and is liquidated
        # alone, so the capital of one flow never pays for another (RF-03.03, docs/architecture.md:178).
        return cls.ISOLATED
