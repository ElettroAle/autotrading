from collections.abc import Callable
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
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from tests.support.flows import OPENROUTER_MODEL, account_id_of, scenario_catalog
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

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
        client.post("/provider-keys", json={"provider": "openrouter", "key": "K-OPENROUTER-TEST"})
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
        "sources": [{"name": "notizie", "weight": 2}],
        "instructions": "compra in tendenza",
        "max_leverage": 5,
        "max_margin_exposure_percent": "10",
        "allocated_capital": "300",
        "bring_to_minimum": True,
    }
    response = client.post("/flows", json=request)
    assert response.status_code == 201
    created: dict[str, Any] = response.json()
    return created


def a_strategy() -> FlowStrategy:
    return FlowStrategy(
        cycle_interval=CycleInterval(60),
        model=ModelSelection(OPENROUTER_MODEL, {"temperature": Decimal("0.5")}),
        sources=(SourceSelection("notizie", 2, {"articoli": 10}),),
        instructions="compra in tendenza",
        risk_limits=RiskLimits(5, Decimal(10)),
        bring_to_minimum=True,
    )


def test_the_document_carries_format_version_and_the_strategy_with_numbers_as_strings() -> None:
    document = StrategyDocument.of(a_strategy()).model_dump(mode="json")

    assert document == {
        "format": "autotrading-strategy",
        "format_version": 1,
        "strategy": {
            "cycle_minutes": 60,
            "model": {"name": OPENROUTER_MODEL, "parameters": {"temperature": "0.5"}},
            "sources": [{"name": "notizie", "weight": 2, "parameters": {"articoli": 10}}],
            "instructions": "compra in tendenza",
            "risk_limits": {
                "max_leverage": 5,
                "max_margin_exposure_percent": "10",
                "max_value_exposure_percent": None,
            },
            "bring_to_minimum": True,
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
    assert [(source.name, source.weight, source.parameters) for source in command.sources] == [
        ("notizie", 2, {"articoli": 10})
    ]
    assert (command.max_leverage, command.max_margin_exposure_percent, command.max_value_exposure_percent) == (
        5,
        Decimal(10),
        None,
    )
    assert (command.instructions, command.bring_to_minimum) == ("compra in tendenza", True)


def test_a_document_without_model_or_limits_gives_them_empty() -> None:
    document = StrategyDocument(format="autotrading-strategy", format_version=1, strategy=StrategyBody())

    command = document.command("alfa bis")

    assert (command.model, command.model_parameters, command.max_leverage, command.sources) == (None, {}, None, ())


@pytest.mark.parametrize(("format_name", "version"), [("altro-formato", 1), ("autotrading-strategy", 2)])
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
    assert (document["format"], document["format_version"]) == ("autotrading-strategy", 1)
    assert document["strategy"]["model"]["name"] == OPENROUTER_MODEL
    assert document["strategy"]["model"]["parameters"]["temperature"] == "0.5"
    assert [(source["name"], source["weight"]) for source in document["strategy"]["sources"]] == [("notizie", 2)]
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
    strategy_parts = ("cycle_minutes", "model", "sources", "instructions", "risk_limits", "bring_to_minimum")
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
        {"detail": "modello non disponibile: openrouter/ritirato"},
    )


def test_an_import_of_another_format_answers_400_with_the_reason(client_of: Client) -> None:
    anna = client_of("anna")
    document = StrategyDocument.of(a_strategy()).model_dump(mode="json")
    document["format_version"] = 2

    response = anna.post("/flows/import", params={"name": "alfa bis"}, json=document)

    assert (response.status_code, reason_of(response)) == (
        400,
        {
            "detail": "formato del file non supportato: autotrading-strategy versione 2",
            "format": "autotrading-strategy",
            "format_version": 2,
        },
    )


def test_an_import_without_name_answers_with_the_reason(client_of: Client) -> None:
    anna = client_of("anna")

    response = anna.post("/flows/import", json=StrategyDocument.of(a_strategy()).model_dump(mode="json"))

    assert (response.status_code, reason_of(response)) == (422, {"detail": "nome del flusso obbligatorio"})
