from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from string import Formatter
from typing import TYPE_CHECKING

from autotrading.domain.flows.errors import MalformedSystemPromptError, UnknownPromptPlaceholderError
from autotrading.domain.flows.risk_limits import LOWEST_LEVERAGE

if TYPE_CHECKING:
    from autotrading.domain.flows.flow_configuration import FlowConfiguration

LIST_SEPARATOR = ", "


@dataclass(frozen=True, slots=True)
class PromptSubject:
    """What the placeholders of the system prompt read: the configuration of the flow and the actions the agent may
    take, which the agent declares (R1.4.8).
    """

    configuration: FlowConfiguration
    actions: tuple[str, ...]


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
        ' "ragionamento": "<perché>"}}]}}',
        "direzione, quota e leva servono solo per apri; obiettivo, stop e invalidazione servono solo per apri e"
        " aggiorna, togli_obiettivo solo per aggiorna; il ragionamento serve sempre.",
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
