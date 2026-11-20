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
from tests.support.source_selections import a_source

ACTIONS = ("apri", "chiudi", "mantieni")
CONFIGURATION = replace(
    a_configuration(assets=("BTC", "ETH")),
    instructions="Sei prudente",
    risk_limits=RiskLimits(3, Decimal(10)),
    sources=(a_source("forecast", 10), a_source("indicatori", 2)),
)
WEIGHT_RULE = "\n".join(
    (
        "- il peso di una fonte è un intero da 1 a 10, predefinito 5: l'importanza relativa che l'utente dà a ogni"
        " fonte;",
        "- quando le fonti sono in disaccordo prevale quella col peso più alto, non il numero dei segnali;",
        "- più valori della stessa fonte (per esempio medie, MACD e RSI degli indicatori) contano come una fonte"
        " sola, col suo peso;",
        "- le istruzioni del flusso prevalgono sui pesi quando li contraddicono;",
        "- nel ragionamento di un'apertura nomina la fonte che ha deciso la direzione quando le fonti erano in"
        " disaccordo;",
        "- una voce senza peso è un aggregato: riassume gli adapter elencati della sua fonte, ciascuno col suo peso;",
    )
)


def test_every_placeholder_declares_its_name_and_what_it_means() -> None:
    assert [(placeholder.value, placeholder.slot) for placeholder in PromptPlaceholder] == [
        ("instructions", "{instructions}"),
        ("actions", "{actions}"),
        ("max_leverage", "{max_leverage}"),
        ("assets", "{assets}"),
        ("source_weights", "{source_weights}"),
    ]
    assert all(placeholder.description for placeholder in PromptPlaceholder)


def test_every_placeholder_reads_its_value_from_the_flow() -> None:
    subject = PromptSubject(CONFIGURATION, ACTIONS)

    assert {placeholder.value: placeholder.value_of(subject) for placeholder in PromptPlaceholder} == {
        "instructions": "Sei prudente",
        "actions": "apri, chiudi, mantieni",
        "max_leverage": "3",
        "assets": "BTC, ETH",
        "source_weights": WEIGHT_RULE
        + "\n- pesi delle fonti attive del flusso: forecast · Prophet 10, indicatori · Hyperliquid 2;",
    }


def test_the_weights_follow_the_order_of_the_configuration() -> None:
    reordered = replace(CONFIGURATION, sources=(a_source("indicatori", 2), a_source("forecast", 10)))

    assert PromptPlaceholder.SOURCE_WEIGHTS.value_of(PromptSubject(reordered, ACTIONS)).endswith(
        "\n- pesi delle fonti attive del flusso: indicatori · Hyperliquid 2, forecast · Prophet 10;"
    )


def test_a_flow_without_active_sources_is_told_so_after_the_rule() -> None:
    alone = replace(CONFIGURATION, sources=())

    assert PromptPlaceholder.SOURCE_WEIGHTS.value_of(PromptSubject(alone, ACTIONS)) == (
        WEIGHT_RULE + "\n- pesi delle fonti attive del flusso: nessuna fonte attiva;"
    )


def test_the_default_gives_the_rule_of_the_weights_among_the_operational_rules() -> None:
    rendered = rendered_system_prompt(DEFAULT_SYSTEM_PROMPT, PromptSubject(CONFIGURATION, ACTIONS))
    rules, _, answer_format = rendered.partition("Rispondi solo con")

    weights = "\n- pesi delle fonti attive del flusso: forecast · Prophet 10, indicatori · Hyperliquid 2;\n"
    assert WEIGHT_RULE + weights in rules
    assert rules.index("- la chiusura è sempre totale;") < rules.index(WEIGHT_RULE)
    assert "peso" not in answer_format


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
    assert "direzione serve solo per apri, quota e leva solo per apri e inverti" in rendered


def test_the_default_asks_how_to_update_the_plan_of_an_open_position() -> None:
    rendered = rendered_system_prompt(DEFAULT_SYSTEM_PROMPT, PromptSubject(CONFIGURATION, ACTIONS))

    assert (
        "- aggiorna cambia il piano di una posizione aperta: obiettivo, stop e invalidazione nuovi, null lascia quelli"
        " in vigore; togli_obiettivo vero toglie l'obiettivo; lo stop non si toglie e non va oltre lo stop predefinito"
        " del flusso;"
    ) in rendered
    assert '"togli_obiettivo": <true per togliere l\'obiettivo, altrimenti false>' in rendered
    assert (
        "obiettivo, stop e invalidazione servono solo per apri, inverti e aggiorna, togli_obiettivo solo per aggiorna"
        in rendered
    )


def test_the_default_explains_the_reversal_of_an_open_position() -> None:
    rendered = rendered_system_prompt(DEFAULT_SYSTEM_PROMPT, PromptSubject(CONFIGURATION, ACTIONS))

    assert (
        "- inverti chiude per intero la posizione aperta dell'asset e nello stesso ciclo apre il lato opposto, con"
        " quota, leva, obiettivo, stop e invalidazione come apri: la direzione è quella opposta alla posizione aperta;"
    ) in rendered


def test_the_default_asks_the_confidence_of_every_decision() -> None:
    rendered = rendered_system_prompt(DEFAULT_SYSTEM_PROMPT, PromptSubject(CONFIGURATION, ACTIONS))

    assert '"confidenza": <intero da 0 a 100, quanto sei convinto della decisione>' in rendered
    assert "il ragionamento e la confidenza servono sempre." in rendered


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
