from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_suspension import OpeningsStatus, OpeningsSuspension
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT, PromptPlaceholder
from tests.support.activity import a_fill
from tests.support.flows import ACCOUNT, OPENROUTER_MODEL, account_id_of, scenario_catalog
from tests.support.identity_provider import IdentityProvider
from tests.support.lifecycle_steps import hold_position
from tests.support.platform import HYPERLIQUID, Platform, new_credentials, registration
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
KEY = "K-OPENROUTER-TEST"
PLACEHOLDERS = [
    {"name": placeholder.value, "description": placeholder.description} for placeholder in PromptPlaceholder
]


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
        client.post("/provider-keys", json={"provider": "openrouter", "key": {"api_key": KEY}})
        return client

    return client


def a_request(platform: Platform, user: str, **changes: Any) -> dict[str, Any]:
    return {
        "name": "alfa",
        "account_id": str(account_id_of(platform, user)),
        "assets": ["BTC", "eth"],
        "model": OPENROUTER_MODEL,
        "model_parameters": {"temperature": "0.5"},
        "sources": [{"name": "notizie", "adapters": [{"name": "RSS", "weight": 7}]}],
        "instructions": "prudente",
        "max_leverage": 5,
        "max_margin_exposure_percent": "10",
        "allocated_capital": "400.00",
        **changes,
    }


def test_a_created_flow_answers_stopped_with_its_whole_configuration(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    request = a_request(platform, "anna")

    response = anna.post("/flows", json=request)

    assert response.status_code == 201
    body = response.json()
    assert body.pop("id")
    sources = body.pop("sources")
    assert body == {
        "name": "alfa",
        "account_id": request["account_id"],
        "status": "fermo",
        "version": 1,
        "assets": ["BTC", "ETH"],
        "cycle_minutes": 15,
        "model": {"name": OPENROUTER_MODEL, "parameters": {"temperature": "0.5"}},
        "instructions": "prudente",
        "risk_limits": {
            "max_leverage": 5,
            "max_margin_exposure_percent": "10",
            "max_value_exposure_percent": None,
            "max_total_margin_exposure_percent": None,
            "max_total_value_exposure_percent": None,
        },
        "allocated_capital": "400",
        "bring_to_minimum": False,
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "system_prompt_is_default": True,
        "system_prompt_placeholders": PLACEHOLDERS,
        "max_consecutive_failures": None,
        "max_daily_loss_percent": None,
        "max_drawdown_percent": None,
        "openings_resume": "manual",
        "default_stop_loss_percent": "5",
        "default_take_profit_percent": None,
        "minimum_confidence": None,
        "memory": {
            "active": False,
            "decisions": 10,
            "days": 30,
            "text_length": 160,
            "all_decisions": False,
            "summary": False,
            "other_assets": False,
        },
        "trailing_stop": {
            "distance_percent": None,
            "activation_percent": None,
            "breakeven_percent": None,
            "max_profit_in_context": False,
        },
        "consecutive_loss_limit": None,
        "account_exposure_for_agent": False,
        "missing": [],
    }
    assert [(source["name"], source["adapters"][0]["weight"]) for source in sources] == [("notizie", 7)]


def test_the_minimum_confidence_is_created_changed_and_removed_with_a_null(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna", minimum_confidence=60)).json()["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"instructions": "aggressivo"}).json()
    changed = anna.patch(f"/flows/{flow_id}", json={"minimum_confidence": 75}).json()
    removed = anna.patch(f"/flows/{flow_id}", json={"minimum_confidence": None}).json()

    assert (untouched["minimum_confidence"], changed["minimum_confidence"]) == (60, 75)
    assert (removed["version"], removed["minimum_confidence"]) == (4, None)
    assert anna.get(f"/flows/{flow_id}/versions/3").json()["minimum_confidence"] == 75
    assert anna.get(f"/flows/{flow_id}/versions/2/differences/4").json() == [
        {"part": "confidenza minima", "before": "60", "after": "nessuna"},
    ]


def test_the_memory_is_created_kept_and_changed_in_a_new_version(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    created = anna.post("/flows", json=a_request(platform, "anna", memory={"decisions": 4})).json()
    flow_id = created["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"instructions": "aggressivo"}).json()
    changed = anna.patch(f"/flows/{flow_id}", json={"memory": {"active": True, "days": 14}}).json()

    defaults = {"text_length": 160, "all_decisions": False, "summary": False, "other_assets": False}
    assert created["memory"] == {"active": False, "decisions": 4, "days": 30} | defaults
    assert untouched["memory"] == created["memory"]
    assert (changed["version"], changed["memory"]) == (3, {"active": True, "decisions": 4, "days": 14} | defaults)
    assert anna.get(f"/flows/{flow_id}/versions/2").json()["memory"] == created["memory"]
    assert anna.get(f"/flows/{flow_id}/versions/2/differences/3").json() == [
        {
            "part": "memoria",
            "before": "non attiva",
            "after": (
                "attiva, 4 decisioni, 14 giorni, motivo fino a 160 caratteri, solo aperture, chiusure e inversioni"
            ),
        }
    ]


def test_the_motive_is_left_whole_and_every_decision_remembered_and_a_null_length_keeps_it(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    memory = {"active": True, "unlimited_text_length": True, "all_decisions": True}
    created = anna.post("/flows", json=a_request(platform, "anna", memory=memory)).json()
    flow_id = created["id"]

    kept = anna.patch(f"/flows/{flow_id}", json={"memory": {"text_length": None, "days": 7}}).json()
    limited = anna.patch(f"/flows/{flow_id}", json={"memory": {"text_length": 300}}).json()

    assert (created["memory"]["text_length"], created["memory"]["all_decisions"]) == (None, True)
    assert (kept["memory"]["text_length"], kept["memory"]["days"]) == (None, 7)
    assert (limited["version"], limited["memory"]["text_length"]) == (3, 300)


def test_the_summary_and_the_other_assets_are_switched_on_and_off_in_a_new_version(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    memory = {"active": True, "summary": True}
    flow_id = anna.post("/flows", json=a_request(platform, "anna", memory=memory)).json()["id"]

    kept = anna.patch(f"/flows/{flow_id}", json={"memory": {"other_assets": True}}).json()
    off = anna.patch(f"/flows/{flow_id}", json={"memory": {"summary": False}}).json()

    assert (kept["version"], kept["memory"]["summary"], kept["memory"]["other_assets"]) == (2, True, True)
    assert (off["version"], off["memory"]["summary"], off["memory"]["other_assets"]) == (3, False, True)
    assert anna.get(f"/flows/{flow_id}/versions/2/differences/3").json() == [
        {
            "part": "memoria",
            "before": (
                "attiva, 10 decisioni, 30 giorni, motivo fino a 160 caratteri, solo aperture, chiusure e inversioni,"
                " riepilogo, altri asset"
            ),
            "after": (
                "attiva, 10 decisioni, 30 giorni, motivo fino a 160 caratteri, solo aperture, chiusure e inversioni,"
                " altri asset"
            ),
        }
    ]


@pytest.mark.parametrize(
    ("memory", "reason"),
    [
        ({"decisions": 51}, {"detail": "le decisioni della memoria vanno da 1 a 50", "field": "memory.decisions"}),
        ({"days": 0}, {"detail": "i giorni della memoria vanno da 1 a 365", "field": "memory.days"}),
        (
            {"text_length": 0},
            {"detail": "la lunghezza del motivo della memoria è un intero positivo", "field": "memory.text_length"},
        ),
        (
            {"text_length": -5},
            {"detail": "la lunghezza del motivo della memoria è un intero positivo", "field": "memory.text_length"},
        ),
    ],
)
def test_a_memory_out_of_range_is_refused_with_the_reason_and_the_field(
    client_of: Client, platform: Platform, memory: dict[str, int], reason: dict[str, str]
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    response = anna.patch(f"/flows/{flow_id}", json={"memory": memory})

    assert (response.status_code, reason_of(response)) == (422, reason)
    assert anna.get("/flows").json()[0]["version"] == 1


def test_the_memory_of_a_flow_off_answers_inactive_and_empty(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    assert anna.get(f"/flows/{flow_id}/memory").json() == {"active": False, "assets": []}


def test_the_memory_of_a_flow_on_answers_what_the_next_cycle_receives(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna", memory={"active": True})).json()["id"]
    planned_at = platform.now - timedelta(hours=1)
    decision = RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "obiettivo raggiunto")
    platform.cycles.record(CycleRecord(UUID(flow_id), planned_at, CycleOutcome.COMPLETED, decisions=(decision,)))

    response = anna.get(f"/flows/{flow_id}/memory")

    assert response.status_code == 200
    assert response.json() == {
        "active": True,
        "assets": [
            {
                "asset": "BTC",
                "entries": [
                    {
                        "planned_at": planned_at.isoformat().replace("+00:00", "Z"),
                        "asset": "BTC",
                        "action": "chiudi",
                        "direction": None,
                        "price": None,
                        "motive": "obiettivo raggiunto",
                        "invalidation": None,
                        "outcome": None,
                    }
                ],
                "summary": [],
                "other_assets": [],
            },
            {"asset": "ETH", "entries": [], "summary": [], "other_assets": []},
        ],
    }


def test_the_memory_of_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    flow_id = client_of("anna").post("/flows", json=a_request(platform, "anna")).json()["id"]

    assert client_of("bruno").get(f"/flows/{flow_id}/memory").status_code == 404


def test_the_protection_defaults_are_created_changed_and_the_take_profit_removed_with_a_null(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    request = a_request(platform, "anna", default_stop_loss_percent="2.5", default_take_profit_percent="10")
    flow_id = anna.post("/flows", json=request).json()["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"default_stop_loss_percent": "3"}).json()
    removed = anna.patch(f"/flows/{flow_id}", json={"default_take_profit_percent": None}).json()

    assert (untouched["default_stop_loss_percent"], untouched["default_take_profit_percent"]) == ("3", "10")
    assert (removed["version"], removed["default_stop_loss_percent"], removed["default_take_profit_percent"]) == (
        3,
        "3",
        None,
    )
    first = anna.get(f"/flows/{flow_id}/versions/1").json()
    assert (first["default_stop_loss_percent"], first["default_take_profit_percent"]) == ("2.5", "10")
    assert anna.get(f"/flows/{flow_id}/versions/1/differences/3").json() == [
        {"part": "stop loss predefinito", "before": "2,5%", "after": "3%"},
        {"part": "take profit predefinito", "before": "10%", "after": "nessuno"},
    ]


def test_the_default_system_prompt_is_offered_with_its_placeholders(client_of: Client) -> None:
    response = client_of("anna").get("/flows/system-prompt")

    assert (response.status_code, response.json()) == (
        200,
        {"system_prompt": DEFAULT_SYSTEM_PROMPT, "system_prompt_placeholders": PLACEHOLDERS},
    )


def test_a_system_prompt_is_written_and_restored_to_the_default(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    created = anna.post("/flows", json=a_request(platform, "anna", system_prompt="{instructions}")).json()
    flow_id = created["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"cycle_minutes": 30}).json()
    restored = anna.patch(f"/flows/{flow_id}", json={"system_prompt": None}).json()

    assert (created["system_prompt"], created["system_prompt_is_default"]) == ("{instructions}", False)
    assert (untouched["version"], untouched["system_prompt"]) == (2, "{instructions}")
    assert (restored["version"], restored["system_prompt"], restored["system_prompt_is_default"]) == (
        3,
        DEFAULT_SYSTEM_PROMPT,
        True,
    )
    assert anna.get(f"/flows/{flow_id}/versions/1").json()["system_prompt"] == "{instructions}"


# ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta:
# a null sent on purpose removes the limit, a field left out keeps it.
def test_an_exposure_sent_as_null_is_removed_and_one_left_out_stays(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    request = a_request(platform, "anna", max_margin_exposure_percent="20", max_value_exposure_percent="40")
    flow_id = anna.post("/flows", json=request).json()["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"instructions": "audace"}).json()
    removed = anna.patch(f"/flows/{flow_id}", json={"max_value_exposure_percent": None}).json()

    assert untouched["risk_limits"] == {
        "max_leverage": 5,
        "max_margin_exposure_percent": "20",
        "max_value_exposure_percent": "40",
        "max_total_margin_exposure_percent": None,
        "max_total_value_exposure_percent": None,
    }
    assert (removed["version"], removed["risk_limits"]) == (
        3,
        {
            "max_leverage": 5,
            "max_margin_exposure_percent": "20",
            "max_value_exposure_percent": None,
            "max_total_margin_exposure_percent": None,
            "max_total_value_exposure_percent": None,
        },
    )


# ADR esposizione-complessiva-nel-controllo-del-rischio: the overall limits travel as the limits per operation.
def test_the_overall_exposures_are_set_kept_removed_and_compared(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    request = a_request(
        platform, "anna", max_total_margin_exposure_percent="30", max_total_value_exposure_percent="150.5"
    )
    created = anna.post("/flows", json=request).json()
    flow_id = created["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"instructions": "audace"}).json()
    changed = anna.patch(f"/flows/{flow_id}", json={"max_total_margin_exposure_percent": "40"}).json()
    removed = anna.patch(f"/flows/{flow_id}", json={"max_total_value_exposure_percent": None}).json()

    totals = [
        (limits["max_total_margin_exposure_percent"], limits["max_total_value_exposure_percent"])
        for limits in (body["risk_limits"] for body in (created, untouched, changed, removed))
    ]
    assert totals == [("30", "150.5"), ("30", "150.5"), ("40", "150.5"), ("40", None)]
    assert anna.get(f"/flows/{flow_id}/versions/1").json()["risk_limits"]["max_total_margin_exposure_percent"] == "30"
    assert anna.get(f"/flows/{flow_id}/versions/2/differences/4").json() == [
        {"part": "esposizione complessiva massima del margine", "before": "30%", "after": "40%"},
        {"part": "esposizione complessiva massima del valore", "before": "150,5%", "after": "nessuno"},
    ]


@pytest.mark.parametrize("percent", ["0", "1001"])
def test_an_overall_exposure_out_of_range_is_refused_with_the_reason_and_the_field(
    client_of: Client, platform: Platform, percent: str
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    response = anna.patch(f"/flows/{flow_id}", json={"max_total_value_exposure_percent": percent})

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "l'esposizione complessiva massima va da 0,1 a 1000", "field": "max_total_value_exposure_percent"},
    )
    assert anna.get("/flows").json()[0]["version"] == 1


def test_a_maximum_of_consecutive_failures_sent_as_null_is_removed_and_one_left_out_stays(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna", max_consecutive_failures=3)).json()["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"instructions": "audace"}).json()
    removed = anna.patch(f"/flows/{flow_id}", json={"max_consecutive_failures": None}).json()

    assert untouched["max_consecutive_failures"] == 3
    assert (removed["version"], removed["max_consecutive_failures"]) == (3, None)


def test_both_exposures_sent_as_null_are_refused_with_the_reason(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    request = a_request(platform, "anna", max_value_exposure_percent="40")
    flow_id = anna.post("/flows", json=request).json()["id"]

    response = anna.patch(
        f"/flows/{flow_id}", json={"max_margin_exposure_percent": None, "max_value_exposure_percent": None}
    )

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "almeno un limite di esposizione è obbligatorio", "field": "max_margin_exposure_percent"},
    )
    assert anna.get("/flows").json()[0]["version"] == 1


def test_a_flow_can_be_created_bringing_its_openings_to_the_exchange_minimum(
    client_of: Client, platform: Platform
) -> None:
    response = client_of("anna").post("/flows", json=a_request(platform, "anna", bring_to_minimum=True))

    assert response.status_code == 201
    assert response.json()["bring_to_minimum"] is True


def test_the_maximum_of_consecutive_failed_cycles_is_set_kept_and_compared(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    created = anna.post("/flows", json=a_request(platform, "anna", max_consecutive_failures=3)).json()
    flow_id = created["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"cycle_minutes": 30}).json()
    changed = anna.patch(f"/flows/{flow_id}", json={"max_consecutive_failures": 5}).json()

    assert created["max_consecutive_failures"] == 3
    assert (untouched["version"], untouched["max_consecutive_failures"]) == (2, 3)
    assert (changed["version"], changed["max_consecutive_failures"]) == (3, 5)
    assert anna.get(f"/flows/{flow_id}/versions/1").json()["max_consecutive_failures"] == 3
    assert anna.get(f"/flows/{flow_id}/versions/2/differences/3").json() == [
        {"part": "cicli falliti consecutivi massimi", "before": "3", "after": "5"}
    ]


@pytest.mark.parametrize("maximum", [0, 101])
def test_a_maximum_of_consecutive_failed_cycles_out_of_range_is_refused(
    client_of: Client, platform: Platform, maximum: int
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    response = anna.patch(f"/flows/{flow_id}", json={"max_consecutive_failures": maximum})

    assert (response.status_code, reason_of(response)) == (
        400,
        {"detail": "il massimo di cicli falliti consecutivi va da 1 a 100", "field": "max_consecutive_failures"},
    )
    assert anna.get("/flows").json()[0]["version"] == 1


def test_the_maximum_losses_and_the_resume_are_set_kept_removed_and_compared(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    request = a_request(
        platform, "anna", max_daily_loss_percent="5", max_drawdown_percent="10", openings_resume="next_day"
    )
    created = anna.post("/flows", json=request).json()
    flow_id = created["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"cycle_minutes": 30}).json()
    changed = anna.patch(f"/flows/{flow_id}", json={"max_daily_loss_percent": None, "openings_resume": "manual"}).json()

    assert (created["max_daily_loss_percent"], created["max_drawdown_percent"], created["openings_resume"]) == (
        "5",
        "10",
        "next_day",
    )
    assert (untouched["max_daily_loss_percent"], untouched["openings_resume"]) == ("5", "next_day")
    assert (changed["max_daily_loss_percent"], changed["max_drawdown_percent"], changed["openings_resume"]) == (
        None,
        "10",
        "manual",
    )
    assert anna.get(f"/flows/{flow_id}/versions/1").json()["openings_resume"] == "next_day"
    assert anna.get(f"/flows/{flow_id}/versions/2/differences/3").json() == [
        {"part": "perdita giornaliera massima", "before": "5%", "after": "nessuno"},
        {"part": "ripresa delle aperture", "before": "il giorno dopo", "after": "manuale"},
    ]


@pytest.mark.parametrize("field", ["max_daily_loss_percent", "max_drawdown_percent"])
def test_a_maximum_loss_out_of_range_is_refused_with_the_reason_and_the_field(
    client_of: Client, platform: Platform, field: str
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    response = anna.patch(f"/flows/{flow_id}", json={field: "101"})

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "la perdita massima va da 0,1 a 100", "field": field},
    )


def test_the_suspension_of_the_openings_is_resumed_by_the_user(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    platform.flows.openings[FlowId(UUID(flow_id))] = OpeningsStatus(
        OpeningsSuspension("perdita giornaliera 6% oltre il 5%", datetime(2026, 11, 12, 9, tzinfo=UTC)), None
    )

    resumed = anna.post(f"/flows/{flow_id}/openings/resume")

    assert resumed.status_code == 204
    assert platform.flows.openings[FlowId(UUID(flow_id))].suspension is None


def test_openings_not_suspended_are_not_resumed_and_another_tenant_finds_nothing(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    refused = anna.post(f"/flows/{flow_id}/openings/resume")
    stranger = client_of("bruno").post(f"/flows/{flow_id}/openings/resume")

    assert (refused.status_code, reason_of(refused)) == (409, {"detail": "le aperture di alfa non sono sospese"})
    assert stranger.status_code == 404


def test_the_flows_of_the_tenant_are_listed_and_the_free_capital_shrinks(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    created = anna.post("/flows", json=a_request(platform, "anna")).json()
    account_id = created["account_id"]

    assert [flow["id"] for flow in anna.get("/flows").json()] == [created["id"]]
    assert anna.get(f"/accounts/{account_id}/free-capital").json() == {
        "amount": "600",
        "currency": "USDC",
        "flows_value": "400",
        "flows_result": "0",
    }
    assert client_of("bruno").get("/flows").json() == []


@pytest.mark.parametrize(
    ("changes", "status", "reason"),
    [
        ({"name": ""}, 422, {"detail": "nome del flusso obbligatorio", "field": "name"}),
        (
            {"model": "openai/inesistente"},
            422,
            {"detail": "modello non disponibile: openai/inesistente", "field": "model"},
        ),
        (
            {"model_parameters": {"temperature": 3}},
            422,
            {"detail": "parametro fuori dai valori ammessi: temperatura", "field": "model_parameters"},
        ),
        ({"assets": ["XYZ"]}, 422, {"detail": "asset non negoziabile sull'exchange: XYZ", "field": "assets"}),
        ({"max_leverage": None}, 422, {"detail": "la leva massima è obbligatoria", "field": "max_leverage"}),
        (
            {"allocated_capital": "1000.01"},
            422,
            {"detail": "capitale allocato oltre il capitale libero: 1000 USDC", "field": "allocated_capital"},
        ),
        ({"account_id": str(uuid4())}, 404, {"detail": "conto non trovato"}),
    ],
)
def test_an_invalid_configuration_answers_with_the_reason_and_the_field_it_concerns(
    client_of: Client, platform: Platform, changes: dict[str, Any], status: int, reason: dict[str, str]
) -> None:
    anna = client_of("anna")

    response = anna.post("/flows", json=a_request(platform, "anna", **changes))

    assert (response.status_code, reason_of(response)) == (status, reason)
    assert anna.get("/flows").json() == []


def test_a_name_already_used_is_a_conflict(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    anna.post("/flows", json=a_request(platform, "anna", allocated_capital="10"))

    response = anna.post("/flows", json=a_request(platform, "anna", allocated_capital="10"))

    assert (response.status_code, reason_of(response)) == (
        409,
        {"detail": "nome già usato da un altro flusso", "field": "name"},
    )


def test_the_free_capital_of_an_account_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    client_of("anna")
    account_id = account_id_of(platform, "anna")

    response = client_of("bruno").get(f"/accounts/{account_id}/free-capital")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "conto non trovato"})


def test_a_flow_is_modified_compared_commanded_and_archived(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    modified = anna.patch(
        f"/flows/{flow_id}", json={"cycle_minutes": 30, "instructions": "audace", "bring_to_minimum": True}
    )

    assert (modified.status_code, modified.json()["version"], modified.json()["cycle_minutes"]) == (200, 2, 30)
    first = anna.get(f"/flows/{flow_id}/versions/1").json()
    assert (
        first["version"],
        first["cycle_minutes"],
        first["instructions"],
        first["allocated_capital"],
        first["bring_to_minimum"],
    ) == (
        1,
        15,
        "prudente",
        "400",
        False,
    )
    assert anna.get(f"/flows/{flow_id}/versions/1/differences/2").json() == [
        {"part": "intervallo di ciclo", "before": "15 minuti", "after": "30 minuti"},
        {"part": "istruzioni", "before": "prudente", "after": "audace"},
        {"part": "porta al minimo", "before": "no", "after": "sì"},
    ]
    assert [anna.post(f"/flows/{flow_id}/{action}").json()["status"] for action in ("start", "pause", "resume")] == [
        "attivo",
        "in pausa",
        "attivo",
    ]
    refused = anna.post(f"/flows/{flow_id}/archive")
    assert (refused.status_code, reason_of(refused)) == (409, {"detail": "si archivia solo un flusso fermo"})


def test_the_versions_of_a_flow_are_listed_newest_first_with_when_each_was_saved(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    platform.flows.now = datetime(2026, 11, 14, 10, 30, tzinfo=UTC)
    anna.patch(f"/flows/{flow_id}", json={"instructions": "audace"})

    response = anna.get(f"/flows/{flow_id}/versions")

    assert response.status_code == 200
    assert response.json() == [
        {"version": 2, "created_at": "2026-11-14T10:30:00Z"},
        {"version": 1, "created_at": "2026-01-01T00:00:00Z"},
    ]
    missing = client_of("bruno").get(f"/flows/{flow_id}/versions")
    assert (missing.status_code, reason_of(missing)) == (404, {"detail": "flusso non trovato"})


def test_an_archived_flow_is_listed_apart(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    archived = anna.post(f"/flows/{flow_id}/archive")

    assert (archived.status_code, archived.json()["status"]) == (200, "archiviato")
    assert anna.get("/flows").json() == []
    assert [flow["id"] for flow in anna.get("/flows", params={"archived": True}).json()] == [flow_id]


def test_an_archived_flow_is_read_alone_with_its_status(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    anna.post(f"/flows/{flow_id}/archive")

    response = anna.get(f"/flows/{flow_id}")

    assert response.status_code == 200
    assert (response.json()["id"], response.json()["name"], response.json()["status"]) == (
        flow_id,
        "alfa",
        "archiviato",
    )


def test_a_flow_of_another_tenant_or_missing_is_not_found_when_read_alone(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    bruno = client_of("bruno")

    for response in (bruno.get(f"/flows/{flow_id}"), anna.get(f"/flows/{uuid4()}")):
        assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})


def test_the_fixed_readings_of_the_flows_are_not_taken_for_a_flow_read_alone(client_of: Client) -> None:
    anna = client_of("anna")

    responses = [anna.get(path) for path in ("/flows/overview", "/flows/ranking", "/flows/system-prompt")]

    assert [response.status_code for response in responses] == [200, 200, 200]


@pytest.mark.parametrize(
    ("changes", "reason", "field"),
    [
        ({"cycle_minutes": 0}, "intervallo di ciclo fuori da 1-1440 minuti", "cycle_minutes"),
        ({"account_id": str(uuid4())}, "il conto di un flusso non si cambia", "account_id"),
        ({"assets": ["XYZ"]}, "asset non negoziabile sull'exchange: XYZ", "assets"),
        (
            {"model": "openai/inesistente", "model_parameters": {}},
            "modello non disponibile: openai/inesistente",
            "model",
        ),
        ({"sources": [{"name": "inesistente"}]}, "fonte non disponibile: inesistente", "sources"),
        (
            {"max_leverage": 0, "max_margin_exposure_percent": "5", "max_value_exposure_percent": "5"},
            "limite di rischio non valido: leva massima",
            "max_leverage",
        ),
        ({"system_prompt": "{leverage}"}, 'il segnaposto "leverage" non esiste', "system_prompt"),
        (
            {"default_stop_loss_percent": "51"},
            "lo stop loss predefinito va da 0,1 a 50",
            "default_stop_loss_percent",
        ),
        (
            {"default_take_profit_percent": "0"},
            "il take profit predefinito è maggiore di 0",
            "default_take_profit_percent",
        ),
        ({"minimum_confidence": -1}, "la confidenza minima va da 0 a 100", "minimum_confidence"),
        ({"minimum_confidence": 101}, "la confidenza minima va da 0 a 100", "minimum_confidence"),
    ],
)
def test_an_invalid_change_answers_with_the_reason_and_the_field_it_concerns(
    client_of: Client, platform: Platform, changes: dict[str, Any], reason: str, field: str
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    response = anna.patch(f"/flows/{flow_id}", json=changes)

    assert (response.status_code, reason_of(response)) == (422, {"detail": reason, "field": field})
    assert anna.get("/flows").json()[0]["version"] == 1


def test_a_flow_of_another_tenant_or_a_missing_version_is_not_found(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    bruno = client_of("bruno")

    for response in (
        bruno.patch(f"/flows/{flow_id}", json={"instructions": "x"}),
        bruno.post(f"/flows/{flow_id}/start"),
        bruno.post(f"/flows/{flow_id}/archive"),
        bruno.get(f"/flows/{flow_id}/versions/1"),
    ):
        assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})
    missing = anna.get(f"/flows/{flow_id}/versions/1/differences/5")
    assert (missing.status_code, reason_of(missing)) == (404, {"detail": "versione di configurazione non trovata: 5"})
    assert anna.post(f"/flows/{flow_id}/explode").status_code == 422
    refused = anna.post(f"/flows/{flow_id}/pause")
    assert (refused.status_code, reason_of(refused)) == (
        409,
        {"detail": "comando pausa non ammesso per un flusso fermo"},
    )


def test_a_stopped_flow_above_the_free_capital_of_now_answers_with_the_reason(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    credentials = new_credentials()
    platform.hyperliquid.accept(credentials)
    platform.register_account("anna", registration(ACCOUNT, HYPERLIQUID, credentials))
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    platform.hyperliquid.accept(credentials, amount=Decimal(300))

    response = anna.post(f"/flows/{flow_id}/start")

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "capitale allocato oltre il capitale libero: 300 USDC", "field": "allocated_capital"},
    )
    assert anna.get("/flows").json()[0]["status"] == "fermo"


def test_a_stop_answers_the_flow_stopped_and_the_positions_left_open(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    anna.post(f"/flows/{flow_id}/start")
    hold_position(platform, "anna", ACCOUNT, "BTC")
    hold_position(platform, "anna", ACCOUNT, "ETH")
    platform.order_exchange.closing_rejections["ETH"] = "Order rejected"

    response = anna.post(f"/flows/{flow_id}/stop")

    assert response.status_code == 200
    body = response.json()
    assert (body["flow"]["id"], body["flow"]["status"]) == (flow_id, "fermo")
    assert body["left_open"] == [{"asset": "ETH", "reason": "Order rejected"}]
    refused = anna.post(f"/flows/{flow_id}/stop")
    assert (refused.status_code, reason_of(refused)) == (
        409,
        {"detail": "comando ferma non ammesso per un flusso fermo"},
    )


def test_the_capital_of_a_flow_changes_with_its_history(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    changed = anna.put(f"/flows/{flow_id}/allocated-capital", json={"allocated_capital": "700.50"})

    assert (changed.status_code, changed.json()["allocated_capital"], changed.json()["version"]) == (200, "700.5", 2)
    (change,) = anna.get(f"/flows/{flow_id}/capital-changes").json()["changes"]
    assert change == {
        "changed_at": platform.now.isoformat().replace("+00:00", "Z"),
        "flow_id": flow_id,
        "flow": "alfa",
        "reason": "aumento",
        "amount": "300.5",
        "previous": "400",
        "new": "700.5",
    }
    refused = anna.put(f"/flows/{flow_id}/allocated-capital", json={"allocated_capital": "1000.51"})
    assert (refused.status_code, reason_of(refused)) == (
        422,
        {"detail": "capitale allocato oltre il capitale disponibile: 1000 USDC", "field": "allocated_capital"},
    )


def earned(platform: Platform, flow_id: str, pnl: str) -> None:
    profit = a_fill("SOL", None, realized_pnl=Decimal(pnl), size=Decimal(0))
    platform.ledger.add(account_id_of(platform, "anna"), FlowId(UUID(flow_id)), profit)


def test_a_cash_out_answers_the_flow_the_capital_kept_and_what_it_freed(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    anna.post(f"/flows/{flow_id}/start")
    earned(platform, flow_id, "118")

    response = anna.post(f"/flows/{flow_id}/cash-out", json={"capital": "300"})

    assert response.status_code == 200
    body = response.json()
    assert (body["flow"]["id"], body["flow"]["status"], body["flow"]["allocated_capital"]) == (flow_id, "attivo", "300")
    assert (body["freed"], body["capital"], body["left_open"]) == ("218", "300", [])


def test_a_cash_out_without_a_body_keeps_the_capital_allocated_now(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    earned(platform, flow_id, "18.5")

    response = anna.post(f"/flows/{flow_id}/cash-out")

    assert (response.status_code, response.json()["freed"], response.json()["capital"]) == (200, "18.5", "400")


def test_a_cash_out_of_a_flow_without_profits_is_a_conflict(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    response = anna.post(f"/flows/{flow_id}/cash-out", json={})

    assert (response.status_code, reason_of(response)) == (409, {"detail": "alfa non ha profitti da incassare"})


def test_stop_and_capital_of_a_flow_of_another_tenant_are_not_found(client_of: Client, platform: Platform) -> None:
    flow_id = client_of("anna").post("/flows", json=a_request(platform, "anna")).json()["id"]
    bruno = client_of("bruno")

    for response in (
        bruno.post(f"/flows/{flow_id}/stop"),
        bruno.post(f"/flows/{flow_id}/cash-out"),
        bruno.put(f"/flows/{flow_id}/allocated-capital", json={"allocated_capital": "10"}),
        bruno.get(f"/flows/{flow_id}/capital-changes"),
    ):
        assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})


def test_an_account_with_an_active_flow_is_removed_only_confirming(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    request = a_request(platform, "anna")
    flow_id = anna.post("/flows", json=request).json()["id"]
    anna.post(f"/flows/{flow_id}/start")

    suspended = anna.delete(f"/accounts/{request['account_id']}")
    removed = anna.delete(f"/accounts/{request['account_id']}", params={"confirmed": True})

    assert (suspended.status_code, reason_of(suspended)) == (
        409,
        {"detail": "il conto ha flussi attivi o in pausa che verranno fermati: alfa"},
    )
    assert removed.status_code == 204
    assert [flow["status"] for flow in anna.get("/flows", params={"archived": True}).json()] == ["archiviato"]


def test_every_part_of_the_stop_that_follows_the_price_is_in_the_answer_even_when_empty(platform: Platform) -> None:
    # R5.5.1: the dashboard generates its types from the document; an empty part is a null, never a missing field.
    api = create_api(HealthReport("1.0.0", "dev"), ResolveTenantUseCase(platform.tenants), platform.for_tenant)
    schemas = api.openapi()["components"]["schemas"]
    trailing = schemas["FlowResponse"]["properties"]["trailing_stop"]["$ref"].rsplit("/", 1)[-1]

    assert set(schemas[trailing]["required"]) == {
        "distance_percent",
        "activation_percent",
        "breakeven_percent",
        "max_profit_in_context",
    }


def test_the_limit_of_consecutive_losses_is_created_kept_and_removed(client_of: Client, platform: Platform) -> None:
    # R5.5.2, ADR limite-di-perdite-consecutive-del-flusso.
    anna = client_of("anna")
    limit = {"max_consecutive_losses": 2, "loss_window_hours": 24, "block_minutes": 120}
    flow_id = anna.post("/flows", json=a_request(platform, "anna", consecutive_loss_limit=limit)).json()["id"]

    untouched = anna.patch(f"/flows/{flow_id}", json={"instructions": "aggressivo"}).json()
    scoped = anna.patch(f"/flows/{flow_id}", json={"consecutive_loss_limit": {**limit, "count_scope": "flusso"}})
    removed = anna.patch(f"/flows/{flow_id}", json={"consecutive_loss_limit": {"remove_limit": True}}).json()

    assert untouched["consecutive_loss_limit"] == {**limit, "count_scope": "asset"}
    assert scoped.json()["consecutive_loss_limit"] == {**limit, "count_scope": "flusso"}
    assert (removed["version"], removed["consecutive_loss_limit"]) == (4, None)
    assert anna.get(f"/flows/{flow_id}/versions/3").json()["consecutive_loss_limit"]["count_scope"] == "flusso"
    assert anna.get(f"/flows/{flow_id}/versions/3/differences/4").json() == [
        {
            "part": "blocco delle riaperture dopo perdite consecutive",
            "before": "2 perdite consecutive in 24 ore, blocco di 120 minuti, ambito flusso",
            "after": "nessuno",
        },
    ]


def test_a_limit_of_consecutive_losses_given_in_part_is_refused_naming_the_setting(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")

    response = anna.post(
        "/flows", json=a_request(platform, "anna", consecutive_loss_limit={"max_consecutive_losses": 2})
    )

    assert (response.status_code, reason_of(response)) == (
        422,
        {
            "detail": "perdite consecutive massime, finestra delle perdite e durata del blocco si impostano insieme",
            "field": "consecutive_loss_limit.max_consecutive_losses",
        },
    )


def test_every_part_of_the_limit_of_consecutive_losses_is_in_the_answer(platform: Platform) -> None:
    # R5.5.2: the dashboard generates its types from the document; the limit is whole or a null.
    api = create_api(HealthReport("1.0.0", "dev"), ResolveTenantUseCase(platform.tenants), platform.for_tenant)
    schemas = api.openapi()["components"]["schemas"]
    [limit, _] = schemas["FlowResponse"]["properties"]["consecutive_loss_limit"]["anyOf"]

    assert set(schemas[limit["$ref"].rsplit("/", 1)[-1]]["required"]) == {
        "max_consecutive_losses",
        "loss_window_hours",
        "block_minutes",
        "count_scope",
    }


def test_the_option_of_the_exposure_of_the_account_is_created_off_turned_on_and_kept(
    client_of: Client, platform: Platform
) -> None:
    # R5.5.5, ADR esposizione-degli-altri-flussi-nel-contesto-dell-agente.
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    turned_on = anna.patch(f"/flows/{flow_id}", json={"account_exposure_for_agent": True}).json()
    kept = anna.patch(f"/flows/{flow_id}", json={"instructions": "aggressivo"}).json()

    assert anna.get(f"/flows/{flow_id}/versions/1").json()["account_exposure_for_agent"] is False
    assert (turned_on["version"], turned_on["account_exposure_for_agent"]) == (2, True)
    assert kept["account_exposure_for_agent"] is True
    assert anna.get(f"/flows/{flow_id}/versions/1/differences/2").json() == [
        {"part": "esposizione del conto nel contesto dell'agente", "before": "no", "after": "sì"},
    ]
