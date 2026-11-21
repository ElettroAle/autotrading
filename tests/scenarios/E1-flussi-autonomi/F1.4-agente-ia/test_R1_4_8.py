from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows import flow_configuration
from autotrading.domain.flows.errors import UnknownPromptPlaceholderError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT, PromptPlaceholder

# A cycle of a real flow on the bridges the worker uses (ADR 0042).
from tests.support.flow_cycle_steps import *  # noqa: F403
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.8-system-prompt-personalizzabile.feature")

FLOW = "alfa"


class PromptChange:
    """The user of the scenario, the flow they read and the refusal of their change, if any."""

    def __init__(self) -> None:
        self.user = ""
        self.read: Flow | None = None
        self.error: AutotradingError | None = None


@pytest.fixture
def prompt_change() -> PromptChange:
    return PromptChange()


def flow_of(flow_cycles: FlowCycles, user: str, name: str) -> Flow:
    flows = flow_cycles.platform.use_cases_of(user).list_flows.execute()
    [flow] = [flow for flow in flows if flow.name.value == name]
    return flow


def modify(flow_cycles: FlowCycles, prompt_change: PromptChange, user: str, **changes: object) -> None:
    prompt_change.user = user
    command = ModifyFlowCommand(flow_cycles.flow(FLOW).id, **changes)  # type: ignore[arg-type]  # each step names the part it changes
    try:
        flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
    except AutotradingError as error:
        prompt_change.error = error


def shows_default(flow: Flow) -> None:
    configuration = flow.configuration
    assert configuration.system_prompt is None
    assert configuration.system_prompt_template == DEFAULT_SYSTEM_PROMPT


# Given


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "(?P<flow>[^"]+)" con asset "(?P<assets>[^"]+)", leva massima '
        r'(?P<leverage>\d+) e istruzioni "(?P<instructions>[^"]+)"$'
    )
)
def configured_flow(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles,
    prompt_change: PromptChange,
    user: str,
    flow: str,
    assets: str,
    leverage: str,
    instructions: str,
) -> None:
    prompt_change.user = user
    flow_cycles.add_flow(user, flow, assets=tuple(asset.strip() for asset in assets.split(",")))
    flow_cycles.reconfigure(
        flow,
        lambda configuration: replace(
            configuration, instructions=instructions, risk_limits=RiskLimits(int(leverage), Decimal(10))
        ),
    )


@given(quoted('che "{user}" imposta il system prompt "{prompt}"'))
@given(quoted('che "{user}" imposta il system prompt "{prompt}" senza il formato della risposta'))
@when(quoted('"{user}" imposta il system prompt "{prompt}"'))
def set_prompt(flow_cycles: FlowCycles, prompt_change: PromptChange, user: str, prompt: str) -> None:
    modify(flow_cycles, prompt_change, user, system_prompt=prompt)


@given(quoted('che "{user}" ha impostato un system prompt personalizzato'))
def custom_prompt(flow_cycles: FlowCycles, prompt_change: PromptChange, user: str) -> None:
    modify(flow_cycles, prompt_change, user, system_prompt="{instructions}")
    assert flow_cycles.flow(FLOW).configuration.system_prompt == "{instructions}"


# When


@when(quoted('"{user}" consulta la configurazione del flusso "{flow}"'))
def read_configuration(flow_cycles: FlowCycles, prompt_change: PromptChange, user: str, flow: str) -> None:
    prompt_change.read = flow_of(flow_cycles, user, flow)


@when(quoted('"{user}" ripristina il system prompt predefinito'))
def restore_default(flow_cycles: FlowCycles, prompt_change: PromptChange, user: str) -> None:
    modify(flow_cycles, prompt_change, user, default_system_prompt=True)


# Then


@then("il system prompt è il testo predefinito, indicato come predefinito")
def default_shown(prompt_change: PromptChange) -> None:
    assert prompt_change.read is not None
    shows_default(prompt_change.read)


@then(quoted('la configurazione elenca i segnaposti "{names}" ciascuno con la sua descrizione'))
def placeholders_listed(names: str) -> None:
    assert [placeholder.value for placeholder in PromptPlaceholder] == [name.strip() for name in names.split(",")]
    assert all(placeholder.description for placeholder in PromptPlaceholder)
    for placeholder in PromptPlaceholder:
        assert f"{{{placeholder}}}" in DEFAULT_SYSTEM_PROMPT


@then(quoted('il system prompt inviato all\'agente è "{prompt}"'))
def prompt_sent(flow_cycles: FlowCycles, prompt: str) -> None:
    assert flow_cycles.system_text() == prompt


@then(quoted('la modifica è rifiutata perché il segnaposto "{placeholder}" non esiste'))
def unknown_placeholder(flow_cycles: FlowCycles, prompt_change: PromptChange, placeholder: str) -> None:
    error = prompt_change.error
    assert isinstance(error, UnknownPromptPlaceholderError)
    assert str(error) == f'il segnaposto "{placeholder}" non esiste'
    assert flow_cycles.flow(FLOW).configuration.system_prompt is None


@then(quoted('la configurazione del flusso "{flow}" mostra il testo predefinito, indicato come predefinito'))
def default_restored(flow_cycles: FlowCycles, prompt_change: PromptChange, flow: str) -> None:
    assert prompt_change.error is None
    restored = flow_of(flow_cycles, prompt_change.user, flow)
    shows_default(restored)
    assert restored.configuration.version == 3


@then("la chiamata al modello chiede comunque la risposta nel formato delle decisioni")
def schema_still_requested(flow_cycles: FlowCycles) -> None:
    assert flow_cycles.system_text() == "Sei un trader prudente"
    assert flow_cycles.model.calls[-1].answer == DECISIONS_FORMAT


@given(quoted('che il flusso "{flow}" segue il system prompt predefinito'))
def follows_default(flow_cycles: FlowCycles, flow: str) -> None:
    assert flow_cycles.flow(flow).configuration.system_prompt is None


@given(quoted('che la piattaforma aggiorna il system prompt predefinito in "{prompt}"'))
def default_updated(monkeypatch: pytest.MonkeyPatch, prompt: str) -> None:
    # A new release of the platform brings another default: the configuration reads the one of the release running.
    monkeypatch.setattr(flow_configuration, "DEFAULT_SYSTEM_PROMPT", prompt)


@then(quoted('il flusso "{flow}" resta alla versione di configurazione {version}'))
def version_kept(flow_cycles: FlowCycles, flow: str, version: str) -> None:
    configuration = flow_cycles.flow(flow).configuration
    assert (configuration.version, configuration.system_prompt) == (int(version), None)


@then(quoted('il flusso "{flow}" ha la versione di configurazione {version} con il system prompt "{prompt}"'))
def version_with_prompt(
    flow_cycles: FlowCycles, prompt_change: PromptChange, flow: str, version: str, prompt: str
) -> None:
    assert prompt_change.error is None
    configuration = flow_of(flow_cycles, prompt_change.user, flow).configuration
    assert (configuration.version, configuration.system_prompt) == (int(version), prompt)
