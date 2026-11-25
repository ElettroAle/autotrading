from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.domain.agent.agent_response import (
    ACTION,
    ASSET,
    CONFIDENCE,
    DECISIONS,
    DIRECTION,
    HIGHEST_CONFIDENCE,
    INVALIDATION,
    LEVERAGE,
    LOWEST_CONFIDENCE,
    MARGIN_FRACTION,
    MOTIVE,
    REASONING,
    REMOVE_TARGET,
    STOP,
    TARGET,
)
from autotrading.domain.agent.decision import TradeAction, TradeDirection

type Schema = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class AnswerFormat:
    """The shape the model is asked to answer in, as a JSON Schema a provider can enforce while it writes (R1.4.5).

    The schema is in the strict form: every field required, an optional one nullable, no field beyond those named.
    It only narrows what the model writes: ranges and the fields an action needs stay with `AgentResponse.read`.
    """

    name: str
    schema: Schema


def _strict_object(properties: Mapping[str, Schema]) -> Schema:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _decisions_schema() -> Schema:
    decision = _strict_object(
        {
            ASSET: {"type": "string"},
            ACTION: {"type": "string", "enum": [action.value for action in TradeAction]},
            DIRECTION: {"type": ["string", "null"], "enum": [*(direction.value for direction in TradeDirection), None]},
            MARGIN_FRACTION: {"type": ["number", "null"]},
            LEVERAGE: {"type": ["integer", "null"]},
            TARGET: {"type": ["number", "null"]},
            STOP: {"type": ["number", "null"]},
            INVALIDATION: {"type": ["string", "null"]},
            REMOVE_TARGET: {"type": "boolean"},
            CONFIDENCE: {"type": "integer", "minimum": LOWEST_CONFIDENCE, "maximum": HIGHEST_CONFIDENCE},
            MOTIVE: {"type": ["string", "null"]},
            REASONING: {"type": "string"},
        }
    )
    return _strict_object({DECISIONS: {"type": "array", "items": decision}})


DECISIONS_FORMAT = AnswerFormat(DECISIONS, _decisions_schema())
