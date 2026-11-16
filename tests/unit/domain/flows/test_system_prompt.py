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
    assert "prezzo di mercato e PnL non realizzato" in rendered
    assert '{"decisioni": [{"asset": "<asset>", "azione": "<una delle azioni ammesse>"' in rendered


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
