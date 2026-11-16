from dataclasses import replace
from decimal import Decimal

import pytest

from autotrading.domain.flows.errors import MalformedSystemPromptError, UnknownPromptPlaceholderError
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.system_prompt import (
    DEFAULT_SYSTEM_PROMPT,
    PromptPlaceholder,
    PromptSubject,
    checked_system_prompt,
    rendered_system_prompt,
)
from tests.support.flows import a_configuration

ACTIONS = ("apri", "chiudi", "mantieni")
CONFIGURATION = replace(
    a_configuration(assets=("BTC", "ETH")), instructions="Sei prudente", risk_limits=RiskLimits(3, Decimal(10))
)


def test_every_placeholder_declares_its_name_and_what_it_means() -> None:
    assert [(placeholder.value, placeholder.slot) for placeholder in PromptPlaceholder] == [
        ("instructions", "{instructions}"),
        ("actions", "{actions}"),
        ("max_leverage", "{max_leverage}"),
        ("assets", "{assets}"),
    ]
    assert all(placeholder.description for placeholder in PromptPlaceholder)


def test_every_placeholder_reads_its_value_from_the_flow() -> None:
    subject = PromptSubject(CONFIGURATION, ACTIONS)

    assert {placeholder.value: placeholder.value_of(subject) for placeholder in PromptPlaceholder} == {
        "instructions": "Sei prudente",
        "actions": "apri, chiudi, mantieni",
        "max_leverage": "3",
        "assets": "BTC, ETH",
    }


def test_the_default_uses_every_placeholder_and_renders_the_rules_and_the_format() -> None:
    rendered = rendered_system_prompt(DEFAULT_SYSTEM_PROMPT, PromptSubject(CONFIGURATION, ACTIONS))

    assert rendered.startswith("Sei prudente\n\nRegole operative:\n- al massimo una posizione per asset;\n")
    assert "- azioni ammesse: apri, chiudi, mantieni;" in rendered
    assert "- leva da 1 a 3;" in rendered
    assert "- una decisione per ciascun asset del flusso: BTC, ETH;" in rendered
    assert (
        "- le posizioni aperte si valutano e si gestiscono solo con prezzo di mercato e PnL non realizzato dello stato"
        " del flusso, letti dall'exchange del conto: i prezzi delle fonti possono venire da un'altra rete o piazza e"
        " servono solo a stimare la direzione del mercato."
    ) in rendered
    assert '"quota": <frazione dei soldi del flusso da impegnare come margine, da 0 a 1>' in rendered
    assert '{"decisioni": [{"asset": "<asset>", "azione": "<una delle azioni ammesse>"' in rendered


def test_the_default_asks_the_exit_plan_of_an_opening() -> None:
    rendered = rendered_system_prompt(DEFAULT_SYSTEM_PROMPT, PromptSubject(CONFIGURATION, ACTIONS))

    assert '"obiettivo": <prezzo obiettivo o null>, "stop": <prezzo di stop o null>' in rendered
    assert """"invalidazione": "<condizione che invalida l'apertura>" o null""" in rendered
    assert (
        "- obiettivo, stop e invalidazione di un'apertura sono facoltativi: per un long lo stop sta sotto il prezzo di"
        " mercato e l'obiettivo sopra, per uno short il contrario; il piano in vigore di ogni posizione aperta è nello"
        " stato del flusso;"
    ) in rendered
    assert "direzione, quota e leva servono solo per apri" in rendered


def test_the_default_asks_how_to_update_the_plan_of_an_open_position() -> None:
    rendered = rendered_system_prompt(DEFAULT_SYSTEM_PROMPT, PromptSubject(CONFIGURATION, ACTIONS))

    assert (
        "- aggiorna cambia il piano di una posizione aperta: obiettivo, stop e invalidazione nuovi, null lascia quelli"
        " in vigore; togli_obiettivo vero toglie l'obiettivo; lo stop non si toglie e non va oltre lo stop predefinito"
        " del flusso;"
    ) in rendered
    assert '"togli_obiettivo": <true per togliere l\'obiettivo, altrimenti false>' in rendered
    assert (
        "obiettivo, stop e invalidazione servono solo per apri e aggiorna, togli_obiettivo solo per aggiorna"
        in rendered
    )


def test_a_template_with_known_placeholders_and_doubled_braces_is_accepted() -> None:
    template = '{instructions} {{"leva": {max_leverage}}} {assets!r:>10}'

    assert checked_system_prompt(template) == template
    assert rendered_system_prompt(template, PromptSubject(CONFIGURATION, ACTIONS)) == (
        "Sei prudente {\"leva\": 3} 'BTC, ETH'"
    )


@pytest.mark.parametrize(
    ("template", "unknown"),
    [
        ("Leva al massimo {leverage}", "leverage"),
        ("{assets.upper}", "assets.upper"),
        ("{0}", "0"),
        ("{}", ""),
        ("{assets:>{width}}", "width"),
    ],
)
def test_a_placeholder_outside_the_registry_is_refused_with_its_name(template: str, unknown: str) -> None:
    with pytest.raises(UnknownPromptPlaceholderError) as refused:
        checked_system_prompt(template)

    assert (refused.value.placeholder, str(refused.value)) == (unknown, f'il segnaposto "{unknown}" non esiste')
    assert refused.value.details == {"field": FlowSetting.SYSTEM_PROMPT.value}


@pytest.mark.parametrize("template", ["{instructions", "graffa } sola", "{"])
def test_a_brace_without_its_pair_is_refused(template: str) -> None:
    with pytest.raises(MalformedSystemPromptError):
        checked_system_prompt(template)


def test_a_configuration_follows_the_default_until_the_user_writes_a_template() -> None:
    assert CONFIGURATION.system_prompt is None
    assert CONFIGURATION.system_prompt_template == DEFAULT_SYSTEM_PROMPT

    own = replace(CONFIGURATION, system_prompt="{instructions} su {assets}")

    assert own.system_prompt_template == "{instructions} su {assets}"
    assert own.rendered_system_prompt(ACTIONS) == "Sei prudente su BTC, ETH"


def test_a_configuration_with_an_unknown_placeholder_cannot_exist() -> None:
    with pytest.raises(UnknownPromptPlaceholderError):
        replace(CONFIGURATION, system_prompt="{leverage}")
