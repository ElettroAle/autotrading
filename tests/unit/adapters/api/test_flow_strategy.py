from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.strategy_document import (
    StrategyBody,
    StrategyDocument,
    StrategyFormatNotSupportedError,
    attachment_of,
)
from autotrading.application.flows.create_flow import (
    ConsecutiveLossLimitRequest,
    MemoryRequest,
    SourceRequest,
    TrailingStopRequest,
)
from autotrading.application.flows.ports import AdapterRequest
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit, LossCountScope
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection
from autotrading.domain.flows.trailing_stop import TrailingStop
from tests.support.flows import OPENROUTER_MODEL, account_id_of, scenario_catalog
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of
from tests.support.source_selections import a_source

Client = Callable[[str], TestClient]


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@pytest.fixture
def client_of(platform: Platform) -> Client:
    provider = IdentityProvider()
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        provider.authentication(),
    )

    def client(user: str) -> TestClient:
        person = platform.directory.person(user)
        person.roles.add("Utente")
        client = TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})
        client.post("/provider-keys", json={"provider": "openrouter", "key": {"api_key": "K-OPENROUTER-TEST"}})
        return client

    return client


def an_original(client: TestClient, platform: Platform, user: str, name: str = "alfa") -> dict[str, Any]:
    request = {
        "name": name,
        "account_id": str(account_id_of(platform, user)),
        "assets": ["BTC"],
        "cycle_minutes": 60,
        "model": OPENROUTER_MODEL,
        "model_parameters": {"temperature": "0.5"},
        "sources": [{"name": "notizie", "adapters": [{"name": "RSS", "weight": 2}]}],
        "instructions": "compra in tendenza",
        "max_leverage": 5,
        "max_margin_exposure_percent": "10",
        "max_total_margin_exposure_percent": "30",
        "allocated_capital": "300",
        "bring_to_minimum": True,
        "system_prompt": "{instructions} su {assets}",
        "max_consecutive_failures": 4,
        "max_daily_loss_percent": "5",
        "max_drawdown_percent": "10",
        "openings_resume": "next_day",
        "memory": {"active": True, "decisions": 5, "days": 14},
    }
    response = client.post("/flows", json=request)
    assert response.status_code == 201
    created: dict[str, Any] = response.json()
    return created


def a_strategy() -> FlowStrategy:
    return FlowStrategy(
        cycle_interval=CycleInterval(60),
        model=ModelSelection(OPENROUTER_MODEL, {"temperature": Decimal("0.5")}),
        sources=(a_source("notizie", 2, {"articoli": 10}),),
        instructions="compra in tendenza",
        risk_limits=RiskLimits(5, Decimal(10), None, Decimal(30), Decimal(200)),
        bring_to_minimum=True,
        system_prompt="{instructions}",
        max_consecutive_failures=3,
        max_daily_loss_percent=Decimal(5),
        max_drawdown_percent=Decimal("12.5"),
        openings_resume=OpeningsResume.NEXT_DAY,
        protection_defaults=ProtectionDefaults(Decimal(3), Decimal(9)),
        minimum_confidence=MinimumConfidence(55),
        memory=FlowMemory(
            active=True, decisions=5, days=14, text_length=None, all_decisions=True, summary=True, other_assets=True
        ),
        trailing_stop=TrailingStop(Decimal(2), Decimal(3), Decimal("1.5"), max_profit_in_context=True),
        consecutive_loss_limit=ConsecutiveLossLimit(2, 24, 120, LossCountScope.FLOW),
    )


def test_the_document_carries_format_version_and_the_strategy_with_numbers_as_strings() -> None:
    document = StrategyDocument.of(a_strategy()).model_dump(mode="json")

    assert document == {
        "format": "autotrading-strategy",
        "format_version": 2,
        "strategy": {
            "cycle_minutes": 60,
            "model": {"name": OPENROUTER_MODEL, "parameters": {"temperature": "0.5"}},
            "sources": [
                {"name": "notizie", "adapters": [{"name": "RSS", "weight": 2, "parameters": {"articoli": 10}}]}
            ],
            "instructions": "compra in tendenza",
            "risk_limits": {
                "max_leverage": 5,
                "max_margin_exposure_percent": "10",
                "max_value_exposure_percent": None,
                "max_total_margin_exposure_percent": "30",
                "max_total_value_exposure_percent": "200",
            },
            "bring_to_minimum": True,
            "system_prompt": "{instructions}",
            "max_consecutive_failures": 3,
            "max_daily_loss_percent": "5",
            "max_drawdown_percent": "12.5",
            "openings_resume": "next_day",
            "default_stop_loss_percent": "3",
            "default_take_profit_percent": "9",
            "minimum_confidence": 55,
            "memory": {
                "active": True,
                "decisions": 5,
                "days": 14,
                "text_length": None,
                "all_decisions": True,
                "summary": True,
                "other_assets": True,
                "unlimited_text_length": True,
            },
            "trailing_stop": {
                "distance_percent": "2",
                "activation_percent": "3",
                "breakeven_percent": "1.5",
                "max_profit_in_context": True,
                "remove_distance": False,
                "remove_activation": False,
                "remove_breakeven": False,
            },
            "consecutive_loss_limit": {
                "max_consecutive_losses": 2,
                "loss_window_hours": 24,
                "block_minutes": 120,
                "count_scope": "flusso",
                "remove_limit": False,
            },
            "account_exposure_for_agent": False,
        },
    }


def test_the_document_becomes_the_command_of_the_import_with_the_chosen_name() -> None:
    document = StrategyDocument.model_validate_json(StrategyDocument.of(a_strategy()).model_dump_json())

    command = document.command("alfa bis")

    assert (command.name, command.model, command.model_parameters, command.cycle_minutes) == (
        "alfa bis",
        OPENROUTER_MODEL,
        {"temperature": Decimal("0.5")},
        60,
    )
    assert command.sources == (SourceRequest("notizie", (AdapterRequest("RSS", 2, {"articoli": 10}),)),)
    assert (command.max_leverage, command.max_margin_exposure_percent, command.max_value_exposure_percent) == (
        5,
        Decimal(10),
        None,
    )
    assert (command.instructions, command.bring_to_minimum, command.system_prompt) == (
        "compra in tendenza",
        True,
        "{instructions}",
    )
    assert command.max_consecutive_failures == 3
    assert (command.max_daily_loss_percent, command.max_drawdown_percent, command.openings_resume) == (
        Decimal(5),
        Decimal("12.5"),
        OpeningsResume.NEXT_DAY,
    )
    assert (command.max_total_margin_exposure_percent, command.max_total_value_exposure_percent) == (
        Decimal(30),
        Decimal(200),
    )
    assert (command.default_stop_loss_percent, command.default_take_profit_percent) == (Decimal(3), Decimal(9))
    assert command.minimum_confidence == 55
    assert command.memory == MemoryRequest(
        active=True,
        decisions=5,
        days=14,
        all_decisions=True,
        summary=True,
        other_assets=True,
        unlimited_text_length=True,
    )
    assert command.memory.applied_to(FlowMemory()) == a_strategy().memory
    assert command.trailing_stop == TrailingStopRequest(
        Decimal(2), Decimal(3), Decimal("1.5"), max_profit_in_context=True
    )
    assert command.trailing_stop.applied_to(TrailingStop()) == a_strategy().trailing_stop
    assert command.consecutive_loss_limit == ConsecutiveLossLimitRequest(2, 24, 120, "flusso")


def test_a_document_without_model_or_limits_gives_them_empty() -> None:
    document = StrategyDocument(format="autotrading-strategy", format_version=2, strategy=StrategyBody())

    command = document.command("alfa bis")

    assert (command.model, command.model_parameters, command.max_leverage, command.sources) == (None, {}, None, ())
    assert command.max_consecutive_failures is None
    assert (command.max_daily_loss_percent, command.max_drawdown_percent, command.openings_resume) == (
        None,
        None,
        OpeningsResume.MANUAL,
    )
    assert (command.max_total_margin_exposure_percent, command.max_total_value_exposure_percent) == (None, None)
    assert command.memory == MemoryRequest()
    assert command.consecutive_loss_limit.applied_to(None) is None


def test_a_document_before_the_adapters_gives_every_source_the_adapter_it_became() -> None:
    """A file of the first version still imports: its sources pass to the new model as the flows did (R4.1.1, ADR
    migrazione-delle-fonti-al-modello-ad-adapter)."""
    document = StrategyDocument.model_validate(
        {
            "format": "autotrading-strategy",
            "format_version": 1,
            "strategy": {
                "sources": [
                    {"name": "sentiment-alternative-me", "weight": 4},
                    {"name": "notizie", "weight": 2, "parameters": {"articoli": 10}},
                    {"name": "sentiment-coinmarketcap", "weight": 6},
                    {"name": "oroscopo"},
                ]
            },
        }
    )

    command = document.command("alfa bis")

    assert command.sources == (
        SourceRequest("sentiment", (AdapterRequest("alternative.me", 4), AdapterRequest("CoinMarketCap", 6))),
        SourceRequest("notizie", (AdapterRequest("RSS", 2, {"articoli": 10}),)),
        SourceRequest("oroscopo", (AdapterRequest("oroscopo"),)),
    )


@pytest.mark.parametrize(("format_name", "version"), [("altro-formato", 2), ("autotrading-strategy", 3)])
def test_a_document_of_another_format_or_version_is_refused(format_name: str, version: int) -> None:
    document = StrategyDocument(format=format_name, format_version=version, strategy=StrategyBody())

    with pytest.raises(StrategyFormatNotSupportedError) as refusal:
        document.command("alfa bis")

    assert (str(refusal.value), refusal.value.status_code, refusal.value.details) == (
        f"formato del file non supportato: {format_name} versione {version}",
        400,
        {"format": format_name, "format_version": version},
    )


def test_the_file_is_named_after_the_flow() -> None:
    assert attachment_of("alfa bis") == "attachment; filename=\"alfa bis.json\"; filename*=UTF-8''alfa%20bis.json"


def test_a_name_beyond_plain_characters_keeps_its_full_form_encoded() -> None:
    assert attachment_of('però "/x"') == (
        "attachment; filename=\"per_ __x_.json\"; filename*=UTF-8''per%C3%B2%20%22%2Fx%22.json"
    )


def test_the_export_downloads_the_strategy_without_account_capital_or_assets(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    original = an_original(anna, platform, "anna")

    response = anna.get(f"/flows/{original['id']}/strategy")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == attachment_of("alfa")
    document = response.json()
    assert (document["format"], document["format_version"]) == ("autotrading-strategy", 2)
    assert document["strategy"]["model"]["name"] == OPENROUTER_MODEL
    assert document["strategy"]["model"]["parameters"]["temperature"] == "0.5"
    assert [
        (source["name"], adapter["name"], adapter["weight"])
        for source in document["strategy"]["sources"]
        for adapter in source["adapters"]
    ] == [("notizie", "RSS", 2)]
    assert (document["strategy"]["cycle_minutes"], document["strategy"]["bring_to_minimum"]) == (60, True)
    assert original["account_id"] not in response.text
    assert {"account_id", "allocated_capital", "assets"}.isdisjoint(document["strategy"])


def test_a_flow_of_another_tenant_is_not_exported(client_of: Client, platform: Platform) -> None:
    original = an_original(client_of("anna"), platform, "anna")

    response = client_of("bruno").get(f"/flows/{original['id']}/strategy")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})


def test_the_exported_file_imports_as_a_draft_with_the_same_strategy(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    original = an_original(anna, platform, "anna")
    file = anna.get(f"/flows/{original['id']}/strategy").text

    response = anna.post(
        "/flows/import", params={"name": "alfa bis"}, content=file, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 201
    draft = response.json()
    assert {key: draft[key] for key in ("name", "status", "version", "account_id", "assets", "allocated_capital")} == {
        "name": "alfa bis",
        "status": "bozza",
        "version": 1,
        "account_id": None,
        "assets": [],
        "allocated_capital": None,
    }
    strategy_parts = (
        "cycle_minutes",
        "model",
        "sources",
        "instructions",
        "risk_limits",
        "bring_to_minimum",
        "system_prompt",
        "max_consecutive_failures",
        "memory",
    )
    assert {key: draft[key] for key in strategy_parts} == {key: original[key] for key in strategy_parts}


def test_an_import_without_model_answers_with_the_reason_and_creates_nothing(client_of: Client) -> None:
    anna = client_of("anna")
    document = StrategyDocument.of(a_strategy()).model_dump(mode="json")
    del document["strategy"]["model"]

    response = anna.post("/flows/import", params={"name": "alfa bis"}, json=document)

    assert (response.status_code, reason_of(response)) == (422, {"detail": "modello mancante"})
    assert anna.get("/flows").json() == []


def test_an_import_of_a_model_out_of_the_catalog_answers_with_the_reason(client_of: Client) -> None:
    anna = client_of("anna")
    document = StrategyDocument.of(a_strategy()).model_dump(mode="json")
    document["strategy"]["model"] = {"name": "openrouter/ritirato", "parameters": {}}

    response = anna.post("/flows/import", params={"name": "alfa bis"}, json=document)

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "modello non disponibile: openrouter/ritirato", "field": "model"},
    )


def test_an_import_of_another_format_answers_400_with_the_reason(client_of: Client) -> None:
    anna = client_of("anna")
    document = StrategyDocument.of(a_strategy()).model_dump(mode="json")
    document["format_version"] = 3

    response = anna.post("/flows/import", params={"name": "alfa bis"}, json=document)

    assert (response.status_code, reason_of(response)) == (
        400,
        {
            "detail": "formato del file non supportato: autotrading-strategy versione 3",
            "format": "autotrading-strategy",
            "format_version": 3,
        },
    )


def test_an_import_without_name_answers_with_the_reason(client_of: Client) -> None:
    anna = client_of("anna")

    response = anna.post("/flows/import", json=StrategyDocument.of(a_strategy()).model_dump(mode="json"))

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "nome del flusso obbligatorio", "field": "name"},
    )


def test_the_option_of_the_exposure_of_the_account_goes_through_the_file_and_is_off_when_missing() -> None:
    # R5.5.5: a file written before the option imports it off.
    strategy = replace(a_strategy(), account_exposure_for_agent=True)
    document = StrategyDocument.model_validate_json(StrategyDocument.of(strategy).model_dump_json())
    older = document.model_dump(mode="json")
    del older["strategy"]["account_exposure_for_agent"]

    assert document.command("copia").account_exposure_for_agent is True
    assert StrategyDocument.model_validate(older).command("copia").account_exposure_for_agent is False
