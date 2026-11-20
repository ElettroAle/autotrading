from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from string import Formatter
from typing import TYPE_CHECKING

from autotrading.domain.flows.errors import MalformedSystemPromptError, UnknownPromptPlaceholderError
from autotrading.domain.flows.risk_limits import LOWEST_LEVERAGE
from autotrading.domain.flows.selections import (
    DEFAULT_WEIGHT,
    MAXIMUM_WEIGHT,
    MINIMUM_WEIGHT,
    ActiveSource,
    SourceSelection,
)

if TYPE_CHECKING:
    from autotrading.domain.flows.flow_configuration import FlowConfiguration

LIST_SEPARATOR = ", "
# The model decides with the weights: the platform only tells it what a weight means, never computes on it (Bug 622).
SOURCE_WEIGHTS_RULE = (
    f"- il peso di una fonte è un intero da {MINIMUM_WEIGHT} a {MAXIMUM_WEIGHT}, predefinito {DEFAULT_WEIGHT}:"
    " l'importanza relativa che l'utente dà a ogni fonte;",
    "- quando le fonti sono in disaccordo prevale quella col peso più alto, non il numero dei segnali;",
    "- più valori della stessa fonte (per esempio medie, MACD e RSI degli indicatori) contano come una fonte sola, col"
    " suo peso;",
    "- le istruzioni del flusso prevalgono sui pesi quando li contraddicono;",
    "- nel ragionamento di un'apertura nomina la fonte che ha deciso la direzione quando le fonti erano in disaccordo;",
    "- una voce senza peso è un aggregato: riassume gli adapter elencati della sua fonte, ciascuno col suo peso;",
)
NO_ACTIVE_SOURCE = "nessuna fonte attiva"


@dataclass(frozen=True, slots=True)
class PromptSubject:
    """What the placeholders of the system prompt read: the configuration of the flow and the actions the agent may
    take, which the agent declares (R1.4.8).
    """

    configuration: FlowConfiguration
    actions: tuple[str, ...]


def _source_weights(sources: tuple[SourceSelection, ...]) -> str:
    """The rule of the weights and the weight of every adapter of every active source, in the order of the
    configuration (R1.3.2, R4.1.1).
    """
    weights = (
        LIST_SEPARATOR.join(
            f"{ActiveSource(source.name, adapter.name).label} {adapter.weight}"
            for source in sources
            for adapter in source.adapters
        )
        or NO_ACTIVE_SOURCE
    )
    return "\n".join((*SOURCE_WEIGHTS_RULE, f"- pesi delle fonti attive del flusso: {weights};"))


class PromptPlaceholder(StrEnum):
    """The only registry of the placeholders of the system prompt: each declares what it means and how its value comes
    from the flow. Default text, check, rendering, API and dashboard all derive from it (R1.4.8, ADR
    system-prompt-del-flusso-come-modello-con-segnaposti).
    """

    description: str
    value_of: Callable[[PromptSubject], str]

    def __new__(cls, name: str, description: str, value_of: Callable[[PromptSubject], str]) -> PromptPlaceholder:
        placeholder = str.__new__(cls, name)
        placeholder._value_ = name
        placeholder.description = description
        placeholder.value_of = value_of
        return placeholder

    INSTRUCTIONS = (
        "instructions",
        "le istruzioni dell'agente del flusso",
        lambda subject: subject.configuration.instructions,
    )
    ACTIONS = (
        "actions",
        "le azioni ammesse per ogni asset",
        lambda subject: LIST_SEPARATOR.join(subject.actions),
    )
    MAX_LEVERAGE = (
        "max_leverage",
        "la leva massima del flusso",
        lambda subject: str(subject.configuration.risk_limits.max_leverage),
    )
    ASSETS = (
        "assets",
        "gli asset del flusso",
        lambda subject: LIST_SEPARATOR.join(subject.configuration.assets),
    )

    SOURCE_WEIGHTS = (
        "source_weights",
        "la regola del peso delle fonti e i pesi delle fonti attive del flusso",
        lambda subject: _source_weights(subject.configuration.sources),
    )

    @property
    def slot(self) -> str:
        """The placeholder as the text of the prompt writes it."""
        return f"{{{self.value}}}"


DEFAULT_SYSTEM_PROMPT = "\n".join(
    (
        PromptPlaceholder.INSTRUCTIONS.slot,
        "",
        "Regole operative:",
        "- al massimo una posizione per asset;",
        f"- azioni ammesse: {PromptPlaceholder.ACTIONS.slot};",
        f"- leva da {LOWEST_LEVERAGE} a {PromptPlaceholder.MAX_LEVERAGE.slot};",
        f"- una decisione per ciascun asset del flusso: {PromptPlaceholder.ASSETS.slot};",
        "- la chiusura è sempre totale;",
        "- obiettivo, stop e invalidazione di un'apertura sono facoltativi: per un long lo stop sta sotto il prezzo di"
        " mercato e l'obiettivo sopra, per uno short il contrario; il piano in vigore di ogni posizione aperta è nello"
        " stato del flusso;",
        "- aggiorna cambia il piano di una posizione aperta: obiettivo, stop e invalidazione nuovi, null lascia quelli"
        " in vigore; togli_obiettivo vero toglie l'obiettivo; lo stop non si toglie e non va oltre lo stop predefinito"
        " del flusso;",
        "- inverti chiude per intero la posizione aperta dell'asset e nello stesso ciclo apre il lato opposto, con"
        " quota, leva, obiettivo, stop e invalidazione come apri: la direzione è quella opposta alla posizione aperta;",
        PromptPlaceholder.SOURCE_WEIGHTS.slot,
        "- le posizioni aperte si valutano e si gestiscono solo con prezzo di mercato e PnL non realizzato dello stato"
        " del flusso, letti dall'exchange del conto: i prezzi delle fonti possono venire da un'altra rete o piazza e"
        " servono solo a stimare la direzione del mercato.",
        "",
        "Rispondi solo con un oggetto JSON in questo formato:",
        '{{"decisioni": [{{"asset": "<asset>", "azione": "<una delle azioni ammesse>", "direzione": "long|short",'
        ' "quota": <frazione dei soldi del flusso da impegnare come margine, da 0 a 1>,'
        ' "leva": <intero>, "obiettivo": <prezzo obiettivo o null>, "stop": <prezzo di stop o null>,'
        """ "invalidazione": "<condizione che invalida l'apertura>" o null,"""
        """ "togli_obiettivo": <true per togliere l'obiettivo, altrimenti false>,"""
        ' "confidenza": <intero da 0 a 100, quanto sei convinto della decisione>,'
        ' "ragionamento": "<perché>"}}]}}',
        "direzione serve solo per apri, quota e leva solo per apri e inverti; obiettivo, stop e invalidazione servono"
        " solo per apri, inverti e aggiorna, togli_obiettivo solo per aggiorna; il ragionamento e la confidenza servono"
        " sempre.",
    )
)


def checked_system_prompt(template: str) -> str:
    """The template whose every placeholder is in the registry; a literal brace is written twice."""
    unknown = next((name for name in _placeholders_in(template) if name not in _NAMES), None)
    if unknown is not None:
        raise UnknownPromptPlaceholderError(unknown)
    return template


def rendered_system_prompt(template: str, subject: PromptSubject) -> str:
    """The template of a configuration, already checked, with the value of each placeholder."""
    return template.format_map({placeholder.value: placeholder.value_of(subject) for placeholder in PromptPlaceholder})


_NAMES = frozenset(placeholder.value for placeholder in PromptPlaceholder)


def _placeholders_in(template: str) -> tuple[str, ...]:
    try:
        parts = tuple(Formatter().parse(template))
    except ValueError as error:
        raise MalformedSystemPromptError from error
    # A format specification may name placeholders of its own, which the rendering would fill too.
    return tuple(
        name
        for _, field, specification, _ in parts
        if field is not None
        for name in (field, *_placeholders_in(specification or ""))
    )
