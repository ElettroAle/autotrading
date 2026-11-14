import logging
from dataclasses import replace
from decimal import Decimal

import pytest

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.errors import FlowNameInUseError, InvalidFlowSettingError
from autotrading.application.flows.export_flow_strategy import (
    ExportFlowStrategyCommand,
)
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import (
    ExposureLimitRequiredError,
    FlowNameRequiredError,
    MaxLeverageRequiredError,
    RepeatedSourceError,
    StrategyModelMissingError,
)
from autotrading.domain.flows.flow import FIRST_VERSION
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from tests.support.flows import OPENROUTER_MODEL
from tests.support.strategies import Strategies


def a_command(**changes: object) -> ImportFlowStrategyCommand:
    command = ImportFlowStrategyCommand(
        name="alfa bis",
        model=OPENROUTER_MODEL,
        max_leverage=3,
        max_margin_exposure_percent=Decimal(10),
        max_value_exposure_percent=Decimal(50),
        model_parameters={"max_tokens": "2048"},
        sources=(SourceRequest("indicatori", 2, {"periodo": 14}), SourceRequest("notizie")),
        instructions="  compra basso  ",
        cycle_minutes=60,
        bring_to_minimum=True,
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
        sources=(SourceSelection("indicatori", 2, {"periodo": 14}), SourceSelection("notizie")),
        instructions="compra basso",
        risk_limits=RiskLimits(3, Decimal(10), Decimal(50)),
        bring_to_minimum=True,
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
        sources=tuple(SourceRequest(source.name, source.weight) for source in strategy.sources),
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
            {"sources": (SourceRequest("notizie"), SourceRequest("notizie"))},
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
