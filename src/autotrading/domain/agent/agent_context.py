import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.agent.decision import TradeAction, TradeDirection
from autotrading.domain.agent.errors import InvalidAgentContextError

LOWEST_LEVERAGE = 1
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
    """An open position of the flow as the exchange shows it."""

    asset: str
    direction: TradeDirection
    size: Decimal
    leverage: int
    entry_price: Decimal
    unrealized_pnl: Decimal
    liquidation_price: Decimal | None


@dataclass(frozen=True, slots=True)
class FlowStateView:
    """The state of the flow alone: never the balance of the account, never another flow (R1.4.3)."""

    currency: str
    allocated_capital: Decimal
    available_liquidity: Decimal
    total_value: Decimal
    return_percent: Decimal
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

    instructions: str
    assets: tuple[str, ...]
    max_leverage: int
    started_at: datetime
    now: datetime
    state: FlowStateView
    sources: tuple[SourceData, ...]
    missing: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None or self.now.tzinfo is None or self.now < self.started_at:
            raise InvalidAgentContextError

    def messages(self) -> tuple[ModelMessage, ModelMessage]:
        """The rules and the response format as the system message, the data of the cycle as the user message."""
        return (
            ModelMessage(MessageRole.SYSTEM, self._system_text()),
            ModelMessage(MessageRole.USER, json.dumps(self._document(), ensure_ascii=False, indent=1)),
        )

    def _system_text(self) -> str:
        actions = ", ".join(action.value for action in TradeAction)
        return "\n".join(
            (
                self.instructions,
                "",
                "Regole operative:",
                "- al massimo una posizione per asset;",
                f"- azioni ammesse: {actions};",
                f"- leva da {LOWEST_LEVERAGE} a {self.max_leverage};",
                f"- una decisione per ciascun asset del flusso: {', '.join(self.assets)};",
                "- la chiusura è sempre totale.",
                "",
                "Rispondi solo con un oggetto JSON in questo formato:",
                '{"decisioni": [{"asset": "<asset>", "azione": "apri|chiudi|mantieni", "direzione": "long|short",'
                ' "quota": <frazione del capitale del flusso da impegnare come margine, da 0 a 1>,'
                ' "leva": <intero>, "ragionamento": "<perché>"}]}',
                "direzione, quota e leva servono solo per apri; il ragionamento serve sempre.",
            )
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
        "liquidita_disponibile": str(state.available_liquidity),
        "valore_complessivo": str(state.total_value),
        "rendimento_dall_avvio_percento": str(state.return_percent),
        "posizioni_aperte": [_position_document(position) for position in state.positions],
    }


def _position_document(position: PositionView) -> dict[str, object]:
    liquidation = position.liquidation_price
    return {
        "asset": position.asset,
        "direzione": position.direction.value,
        "dimensione": str(position.size),
        "leva": position.leverage,
        "prezzo_di_ingresso": str(position.entry_price),
        "pnl_non_realizzato": str(position.unrealized_pnl),
        "prezzo_di_liquidazione": None if liquidation is None else str(liquidation),
    }


def _source_document(source: SourceData) -> dict[str, object]:
    return {"fonte": source.source, "peso": source.weight, "asset": source.asset, "valori": dict(source.values)}
