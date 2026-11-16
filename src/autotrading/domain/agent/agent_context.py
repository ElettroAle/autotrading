import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.agent.decision import TradeDirection
from autotrading.domain.agent.errors import InvalidAgentContextError
from autotrading.domain.agent.exit_plan import ExitPlan

MINUTE = timedelta(minutes=1)


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True, slots=True)
class PositionView:
    """An open position of the flow as the exchange shows it, with the exit plan in force (R3.1.1)."""

    asset: str
    direction: TradeDirection
    size: Decimal
    leverage: int
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    liquidation_price: Decimal | None
    exit_plan: ExitPlan = field(default_factory=ExitPlan)


@dataclass(frozen=True, slots=True)
class FlowStateView:
    """The state of the flow alone: never the balance of the account, never another flow (R1.4.3)."""

    currency: str
    allocated_capital: Decimal
    funds: Decimal
    available_liquidity: Decimal
    total_value: Decimal
    # None when no return can be measured (R3.4.3).
    return_percent: Decimal | None
    positions: tuple[PositionView, ...]


@dataclass(frozen=True, slots=True)
class SourceData:
    """The values one active source collected in the cycle; asset is None for a source of the whole market."""

    source: str
    weight: int
    asset: str | None
    values: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Everything the agent receives in a cycle, and nothing else (R1.4.3)."""

    # The flow writes it, from its template and its values: the agent declares only the data and the answer (R1.4.8).
    system_prompt: str
    assets: tuple[str, ...]
    started_at: datetime
    now: datetime
    state: FlowStateView
    sources: tuple[SourceData, ...]
    missing: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None or self.now.tzinfo is None or self.now < self.started_at:
            raise InvalidAgentContextError

    def messages(self) -> tuple[ModelMessage, ModelMessage]:
        """The system prompt of the flow as the system message, the data of the cycle as the user message."""
        return (
            ModelMessage(MessageRole.SYSTEM, self.system_prompt),
            ModelMessage(MessageRole.USER, json.dumps(self._document(), ensure_ascii=False, indent=1)),
        )

    def _document(self) -> dict[str, object]:
        return {
            "ora_corrente": self.now.isoformat(timespec="minutes"),
            "tempo_dall_avvio": elapsed_text(self.now - self.started_at),
            "stato_del_flusso": _state_document(self.state),
            "fonti": [_source_document(source) for source in self.sources],
            "dati_mancanti": list(self.missing),
        }


def elapsed_text(elapsed: timedelta) -> str:
    """The time since the start in days, hours and minutes, as a person would say it."""
    minutes = elapsed // MINUTE
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    parts = [
        _counted(days, "giorno", "giorni"),
        _counted(hours, "ora", "ore"),
        _counted(minutes, "minuto", "minuti"),
    ]
    spoken = [part for part in parts if part]
    if not spoken:
        return "0 minuti"
    if len(spoken) == 1:
        return spoken[0]
    return ", ".join(spoken[:-1]) + " e " + spoken[-1]


def _counted(amount: int, one: str, many: str) -> str:
    if amount == 0:
        return ""
    return f"{amount} {one if amount == 1 else many}"


def _state_document(state: FlowStateView) -> dict[str, object]:
    return {
        "valuta": state.currency,
        "capitale_allocato": str(state.allocated_capital),
        "soldi_del_flusso": str(state.funds),
        "liquidita_disponibile": str(state.available_liquidity),
        "valore_complessivo": str(state.total_value),
        "rendimento_dall_avvio_percento": None if state.return_percent is None else str(state.return_percent),
        "posizioni_aperte": [_position_document(position) for position in state.positions],
    }


def _position_document(position: PositionView) -> dict[str, object]:
    liquidation, plan = position.liquidation_price, position.exit_plan
    return {
        "asset": position.asset,
        "direzione": position.direction.value,
        "dimensione": str(position.size),
        "leva": position.leverage,
        "prezzo_di_ingresso": str(position.entry_price),
        "prezzo_di_mercato": str(position.mark_price),
        "pnl_non_realizzato": str(position.unrealized_pnl),
        "prezzo_di_liquidazione": _text_or_none(liquidation),
        "obiettivo": _text_or_none(plan.target),
        "stop": _text_or_none(plan.stop),
        "invalidazione": plan.invalidation,
    }


def _text_or_none(price: Decimal | None) -> str | None:
    return None if price is None else str(price)


def _source_document(source: SourceData) -> dict[str, object]:
    return {"fonte": source.source, "peso": source.weight, "asset": source.asset, "valori": dict(source.values)}
