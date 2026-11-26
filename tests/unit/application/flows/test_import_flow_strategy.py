import logging
from dataclasses import replace
from decimal import Decimal

import pytest

from autotrading.application.flows.create_flow import ConsecutiveLossLimitRequest, MemoryRequest, SourceRequest
from autotrading.application.flows.errors import FlowNameInUseError, InvalidFlowSettingError
from autotrading.application.flows.export_flow_strategy import (
    ExportFlowStrategyCommand,
)
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.application.flows.ports import AdapterRequest
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit, LossCountScope
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import (
    ExposureLimitRequiredError,
    FlowNameRequiredError,
    MaxLeverageRequiredError,
    RepeatedSourceError,
    StrategyModelMissingError,
)
from autotrading.domain.flows.flow import FIRST_VERSION
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection
from tests.support.flows import OPENROUTER_MODEL
from tests.support.source_selections import a_source, a_source_request
from tests.support.strategies import Strategies


def a_command(**changes: object) -> ImportFlowStrategyCommand:
    command = ImportFlowStrategyCommand(
        name="alfa bis",
        model=OPENROUTER_MODEL,
        max_leverage=3,
        max_margin_exposure_percent=Decimal(10),
        max_value_exposure_percent=Decimal(50),
        max_total_margin_exposure_percent=Decimal(30),
        max_total_value_exposure_percent=Decimal(120),
        model_parameters={"max_tokens": "2048"},
        sources=(a_source_request("indicatori", 2, {"periodo": 14}), a_source_request("notizie")),
        instructions="  compra basso  ",
        cycle_minutes=60,
        bring_to_minimum=True,
        system_prompt="{instructions}",
        max_consecutive_failures=5,
        max_daily_loss_percent=Decimal(5),
        max_drawdown_percent=Decimal(10),
        openings_resume=OpeningsResume.NEXT_DAY,
        default_stop_loss_percent=Decimal(4),
        default_take_profit_percent=Decimal(12),
        minimum_confidence=65,
        memory=MemoryRequest(active=True, decisions=6),
    )
    return replace(command, **changes)  # type: ignore[arg-type]  # each test names the part it changes


@pytest.fixture
def strategies() -> Strategies:
    return Strategies()


def test_the_import_saves_a_draft_at_its_first_version_with_the_strategy_checked(
    strategies: Strategies, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        draft = strategies.import_.execute(a_command())

    assert strategies.repository.get(draft.id) == draft
    assert (draft.tenant_id, draft.name, draft.status, draft.account_id) == (
        strategies.tenant_id,
        FlowName("alfa bis"),
        FlowStatus.DRAFT,
        None,
    )
    assert draft.configuration == FlowStrategy(
        cycle_interval=CycleInterval(60),
        model=ModelSelection(OPENROUTER_MODEL, {"temperature": Decimal(1), "max_tokens": "2048"}),
        sources=(a_source("indicatori", 2, {"periodo": 14}), a_source("notizie")),
        instructions="compra basso",
        risk_limits=RiskLimits(3, Decimal(10), Decimal(50), Decimal(30), Decimal(120)),
        bring_to_minimum=True,
        system_prompt="{instructions}",
        max_consecutive_failures=5,
        max_daily_loss_percent=Decimal(5),
        max_drawdown_percent=Decimal(10),
        openings_resume=OpeningsResume.NEXT_DAY,
        protection_defaults=ProtectionDefaults(Decimal(4), Decimal(12)),
        minimum_confidence=MinimumConfidence(65),
        memory=FlowMemory(active=True, decisions=6, days=30),
    ).draft_configuration(FIRST_VERSION)
    assert [(record.getMessage(), record.__dict__["flow_id"]) for record in caplog.records] == [
        ("strategia importata", str(draft.id.value))
    ]


def test_the_exported_strategy_imports_as_it_was(strategies: Strategies) -> None:
    original = strategies.original()
    strategy = strategies.export.execute(ExportFlowStrategyCommand(original.id)).strategy
    command = ImportFlowStrategyCommand(
        name="alfa bis",
        model=strategy.model.name,
        max_leverage=strategy.risk_limits.max_leverage,
        max_margin_exposure_percent=strategy.risk_limits.max_margin_exposure_percent,
        max_value_exposure_percent=strategy.risk_limits.max_value_exposure_percent,
        sources=tuple(
            SourceRequest(
                source.name, tuple(AdapterRequest(adapter.name, adapter.weight) for adapter in source.adapters)
            )
            for source in strategy.sources
        ),
        instructions=strategy.instructions,
        cycle_minutes=strategy.cycle_interval.minutes,
    )

    draft = strategies.import_.execute(command)

    assert FlowStrategy.of(draft.configuration) == FlowStrategy.of(original.configuration)


@pytest.mark.parametrize(
    ("change", "refusal", "reason"),
    [
        ({"model": None}, StrategyModelMissingError, "modello mancante"),
        ({"model": " "}, StrategyModelMissingError, "modello mancante"),
        ({"model": "openrouter/ritirato"}, InvalidFlowSettingError, "modello non disponibile: openrouter/ritirato"),
        ({"sources": (SourceRequest("balene"),)}, InvalidFlowSettingError, "fonte non disponibile: balene"),
        (
            {"sources": (a_source_request("notizie"), a_source_request("notizie"))},
            RepeatedSourceError,
            "fonte ripetuta: notizie",
        ),
        ({"max_leverage": None}, MaxLeverageRequiredError, "la leva massima è obbligatoria"),
        (
            {"max_margin_exposure_percent": None, "max_value_exposure_percent": None},
            ExposureLimitRequiredError,
            "almeno un limite di esposizione è obbligatorio",
        ),
        ({"name": " "}, FlowNameRequiredError, "nome del flusso obbligatorio"),
    ],
)
def test_an_invalid_file_is_refused_with_the_reason_and_creates_nothing(
    strategies: Strategies, change: dict[str, object], refusal: type[AutotradingError], reason: str
) -> None:
    with pytest.raises(refusal) as refused:
        strategies.import_.execute(a_command(**change))

    assert str(refused.value) == reason
    assert strategies.repository.list() == []


def test_a_name_taken_by_another_flow_is_refused_before_the_strategy_is_checked(strategies: Strategies) -> None:
    strategies.original()

    with pytest.raises(FlowNameInUseError):
        strategies.import_.execute(a_command(name="alfa"))

    assert strategies.models.asked == []
    assert len(strategies.repository.list()) == 1


def test_the_import_saves_the_limit_of_consecutive_losses_of_the_file(strategies: Strategies) -> None:
    command = a_command(consecutive_loss_limit=ConsecutiveLossLimitRequest(2, 24, 120, "flusso"))

    draft = strategies.import_.execute(command)

    assert draft.configuration.consecutive_loss_limit == ConsecutiveLossLimit(2, 24, 120, LossCountScope.FLOW)


def test_the_draft_of_a_strategy_keeps_the_option_of_the_exposure_of_the_account() -> None:
    # R5.5.5, ADR esposizione-degli-altri-flussi-nel-contesto-dell-agente.
    draft = Strategies().import_.execute(a_command(account_exposure_for_agent=True))

    assert draft.configuration.account_exposure_for_agent is True
