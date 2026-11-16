from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.cycles import FlowOverviewResponse
from autotrading.application.flows.list_flow_overviews import FlowOverview
from autotrading.application.flows.ports import FlowSummary
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import (
    AbsentSource,
    CycleFailure,
    CycleOutcome,
    CycleRecord,
    StepDocument,
)
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import FlowTotals
from tests.support.flows import a_configuration, a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
PLANNED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)


@pytest.fixture
def platform() -> Platform:
    return Platform()


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
        return TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})

    return client


def flow_of(platform: Platform, user: str) -> UUID:
    flow = a_flow(platform.tenant_of(user))
    platform.flows.flows.append(flow)
    return flow.id.value


def a_completed_cycle(flow_id: UUID, planned_at: datetime = PLANNED) -> CycleRecord:
    return CycleRecord(
        flow_id=flow_id,
        planned_at=planned_at,
        outcome=CycleOutcome.COMPLETED,
        started_at=planned_at + timedelta(seconds=2),
        steps=(CycleStep.READ_FLOW_STATE, CycleStep.AGENT_DECISION),
        absent_sources=(AbsentSource("notizie", "nessuna risposta entro 60 secondi"),),
        documents=(
            StepDocument(CycleStep.READ_FLOW_STATE, {"versione": 3}),
            StepDocument(CycleStep.AGENT_DECISION, {"decisioni": [{"asset": "BTC", "azione": "apri"}]}),
        ),
        cost=CallCost(2000, 500, Decimal("0.0031")),
    )


def test_the_cycles_of_a_flow_answer_from_the_most_recent(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    platform.cycles.record(a_completed_cycle(flow_id, PLANNED - timedelta(minutes=15)))
    platform.cycles.record(a_completed_cycle(flow_id))

    response = anna.get(f"/flows/{flow_id}/cycles")

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["has_next"]) == (1, False)
    assert [cycle["planned_at"] for cycle in body["cycles"]] == ["2026-11-12T10:07:00Z", "2026-11-12T09:52:00Z"]
    assert body["cycles"][0] == {
        "planned_at": "2026-11-12T10:07:00Z",
        "started_at": "2026-11-12T10:07:02Z",
        "outcome": "concluso",
        "failure": None,
        "decisions": {"decisioni": [{"asset": "BTC", "azione": "apri"}]},
    }


def test_a_failed_or_skipped_cycle_answers_without_decisions(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    failure = CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "fornitore IA non raggiungibile")
    platform.cycles.record(CycleRecord(flow_id, PLANNED, CycleOutcome.FAILED, PLANNED, failure=failure))
    platform.cycles.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=15)))

    cycles = anna.get(f"/flows/{flow_id}/cycles").json()["cycles"]

    assert [(cycle["outcome"], cycle["decisions"]) for cycle in cycles] == [("saltato", None), ("fallito", None)]
    assert cycles[1]["failure"] == {
        "step": "decisione dell'agente",
        "error_type": "ModelUnavailableError",
        "message": "fornitore IA non raggiungibile",
    }


def test_the_page_of_the_cycles_is_chosen_by_the_query(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    for minute in range(51):
        platform.cycles.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=minute)))

    first, second = anna.get(f"/flows/{flow_id}/cycles").json(), anna.get(f"/flows/{flow_id}/cycles?page=2").json()

    assert (len(first["cycles"]), first["has_next"]) == (50, True)
    assert (second["page"], [cycle["planned_at"] for cycle in second["cycles"]]) == (2, ["2026-11-12T10:07:00Z"])


def test_a_page_before_the_first_is_refused(client_of: Client, platform: Platform) -> None:
    response = client_of("anna").get(f"/flows/{flow_of(platform, 'anna')}/cycles?page=0")

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "numero di pagina non valido: le pagine partono da 1"}


def test_the_detail_of_a_cycle_answers_with_everything_recorded(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    platform.cycles.record(a_completed_cycle(flow_id))

    response = anna.get(f"/flows/{flow_id}/cycles/2026-11-12T10:07:00Z")

    assert response.status_code == 200
    assert response.json() == {
        "planned_at": "2026-11-12T10:07:00Z",
        "started_at": "2026-11-12T10:07:02Z",
        "delay_seconds": None,
        "outcome": "concluso",
        "failure": None,
        "steps": ["lettura dello stato del flusso", "decisione dell'agente"],
        "absent_sources": [{"source": "notizie", "reason": "nessuna risposta entro 60 secondi"}],
        "documents": [
            {"step": "lettura dello stato del flusso", "content": {"versione": 3}},
            {"step": "decisione dell'agente", "content": {"decisioni": [{"asset": "BTC", "azione": "apri"}]}},
        ],
        "cost": {"input_tokens": 2000, "output_tokens": 500, "cost_usd": "0.0031"},
    }


def test_a_cycle_without_a_model_call_has_no_cost(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    platform.cycles.record(CycleRecord(flow_id, PLANNED, CycleOutcome.COMPLETED, cost=CallCost(10, 5, None)))
    platform.cycles.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=15)))

    priced = anna.get(f"/flows/{flow_id}/cycles/2026-11-12T10:07:00Z").json()
    skipped = anna.get(f"/flows/{flow_id}/cycles/2026-11-12T10:22:00Z").json()

    assert priced["cost"] == {"input_tokens": 10, "output_tokens": 5, "cost_usd": None}
    assert skipped["cost"] is None


def test_a_cycle_never_recorded_is_not_found(client_of: Client, platform: Platform) -> None:
    response = client_of("anna").get(f"/flows/{flow_of(platform, 'anna')}/cycles/2026-11-12T10:07:00Z")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "ciclo non trovato"}


def test_the_cost_of_a_flow_answers_with_its_total_and_its_days(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    platform.cycles.record(a_completed_cycle(flow_id, PLANNED - timedelta(days=1)))
    platform.cycles.record(a_completed_cycle(flow_id))
    platform.cycles.record(
        CycleRecord(flow_id, PLANNED + timedelta(hours=1), CycleOutcome.COMPLETED, cost=CallCost(1, 1, None))
    )

    response = anna.get(f"/flows/{flow_id}/cost")

    assert response.status_code == 200
    assert response.json() == {
        "total_usd": "0.0062",
        "days": [{"day": "2026-11-11", "cost_usd": "0.0031"}, {"day": "2026-11-12", "cost_usd": "0.0031"}],
        "unavailable_calls": 1,
    }


@pytest.mark.parametrize("path", ["/cycles", "/cycles/2026-11-12T10:07:00Z", "/cost"])
def test_the_cycles_of_a_flow_of_another_user_do_not_exist(client_of: Client, platform: Platform, path: str) -> None:
    flow_id = flow_of(platform, "bruno")
    platform.cycles.record(a_completed_cycle(flow_id))

    response = client_of("anna").get(f"/flows/{flow_id}{path}")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}


def test_a_flow_never_created_does_not_exist(client_of: Client) -> None:
    response = client_of("anna").get(f"/flows/{uuid4()}/cycles")

    assert response.status_code == 404


def test_a_draft_in_use_answers_without_currency_nor_capital(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    draft = a_flow(platform.tenant_of("anna")).duplicated()
    platform.flows.flows.append(draft)

    [overview] = anna.get("/flows/overview").json()

    assert overview["status"] == "bozza"
    keys = ("currency", "initial_capital", "current_capital", "return_percent", "summary")
    assert [overview[key] for key in keys] == [None, None, None, None, None]


def test_the_flows_in_use_answer_with_their_last_and_next_cycle(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = a_flow(
        platform.tenant_of("anna"),
        status=FlowStatus.ACTIVE,
        configuration=a_configuration(allocated_capital=Decimal(300)),
    )
    platform.flows.flows.append(flow)
    platform.flows.anchors[flow.id] = PLANNED - timedelta(minutes=15)
    platform.cycles.record(CycleRecord(flow.id.value, PLANNED - timedelta(minutes=15), CycleOutcome.FAILED))
    platform.cycles.record(a_completed_cycle(flow.id.value))
    platform.ledger.totals[flow.id] = FlowTotals(flow.id, Decimal(30))
    platform.now = PLANNED + timedelta(minutes=1)
    paused = a_flow(platform.tenant_of("anna"), name="beta", status=FlowStatus.PAUSED)
    platform.ledger.totals[paused.id] = FlowTotals(paused.id, Decimal(0), Decimal("10.5"))
    platform.flows.flows.append(paused)
    platform.flows.pause_reasons[paused.id] = "credito esaurito presso openrouter"
    platform.flows.flows.append(a_flow(platform.tenant_of("bruno"), name="omega"))

    response = anna.get("/flows/overview")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(flow.id.value),
            "name": "alfa",
            "account": "",
            "environment": "dev",
            "status": "attivo",
            "pause_reason": None,
            "model": flow.configuration.model.name,
            "version": flow.configuration.version,
            "last_cycle": {"planned_at": "2026-11-12T10:07:00Z", "outcome": "concluso"},
            "next_cycle_at": "2026-11-12T10:22:00Z",
            "currency": "USDC",
            "initial_capital": "300",
            "current_capital": "330",
            "return_percent": "10.00",
            "recent_outcomes": [
                {"planned_at": "2026-11-12T10:07:00Z", "outcome": "concluso"},
                {"planned_at": "2026-11-12T09:52:00Z", "outcome": "fallito"},
            ],
            "summary": {
                "total_gain": "30",
                "total_gain_percent": "10.00",
                "period_gain": "0",
                "period_gain_percent": "0.00",
                "open_positions": 0,
                "failed_cycles": 1,
            },
        },
        {
            "id": str(paused.id.value),
            "name": "beta",
            "account": "",
            "environment": "dev",
            "status": "in pausa",
            "pause_reason": "credito esaurito presso openrouter",
            "model": paused.configuration.model.name,
            "version": paused.configuration.version,
            "last_cycle": None,
            "next_cycle_at": None,
            "currency": "USDC",
            "initial_capital": "100",
            "current_capital": "89.5",
            "return_percent": "-10.50",
            "recent_outcomes": [],
            "summary": {
                "total_gain": "-10.5",
                "total_gain_percent": "-10.50",
                "period_gain": "0",
                "period_gain_percent": "0.00",
                "open_positions": 0,
                "failed_cycles": 0,
            },
        },
    ]


def test_a_flow_without_initial_capital_answers_without_a_return() -> None:
    summary = FlowSummary(uuid4(), "alfa", "test-1", "fermo", None, "openrouter/deepseek-chat", None, 1)
    state = FlowState(FlowId.new(), "USDC", Decimal(0), (), Decimal("12.50"), Decimal(0), Decimal(0))
    overview = FlowOverview(summary, "dev", (), None, FlowResults(state, Decimal(0), 0))

    response = FlowOverviewResponse.of(overview)

    assert (response.initial_capital, response.current_capital, response.return_percent) == ("0", "12.5", None)
    assert response.summary is not None
    assert (response.summary.total_gain_percent, response.summary.period_gain_percent) == (None, None)


def test_the_flows_in_use_answer_their_results_in_the_period_asked_for(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = a_flow(platform.tenant_of("anna"), configuration=a_configuration(allocated_capital=Decimal(100)))
    platform.flows.flows.append(flow)
    platform.now = PLANNED
    platform.cycles.record(CycleRecord(flow.id.value, PLANNED - timedelta(days=8), CycleOutcome.FAILED))
    platform.cycles.record(CycleRecord(flow.id.value, PLANNED - timedelta(days=1), CycleOutcome.FAILED))
    record_equity(platform, flow.id.value, PLANNED - timedelta(days=6), "102.1")
    record_equity(platform, flow.id.value, PLANNED - timedelta(days=1), "102.5")

    [overview] = anna.get("/flows/overview?period=7d").json()

    assert overview["summary"]["period_gain"] == "0.4"
    assert overview["summary"]["period_gain_percent"] == "0.40"
    assert overview["summary"]["failed_cycles"] == 1


def test_the_flows_in_use_refuse_a_period_the_user_cannot_have_meant(client_of: Client) -> None:
    response = client_of("anna").get("/flows/overview?period=range&from=2026-11-12")

    assert (response.status_code, reason_of(response)) == (
        400,
        {"detail": "periodo non valido: un intervallo ha il giorno iniziale e il giorno finale"},
    )


def test_the_cycles_of_a_flow_answer_only_the_failed_ones_when_asked(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    platform.cycles.record(a_completed_cycle(flow_id, PLANNED - timedelta(minutes=15)))
    platform.cycles.record(CycleRecord(flow_id, PLANNED, CycleOutcome.FAILED, PLANNED))

    cycles = anna.get(f"/flows/{flow_id}/cycles?outcome=fallito").json()["cycles"]

    assert [(cycle["planned_at"], cycle["outcome"]) for cycle in cycles] == [("2026-11-12T10:07:00Z", "fallito")]


def test_the_cycles_of_a_flow_refuse_an_outcome_no_cycle_has(client_of: Client, platform: Platform) -> None:
    flow_id = flow_of(platform, "anna")

    response = client_of("anna").get(f"/flows/{flow_id}/cycles?outcome=failed")

    assert (response.status_code, reason_of(response)) == (
        400,
        {"detail": "esito non valido: scegliere tra concluso, fallito, saltato"},
    )


def record_equity(platform: Platform, flow_id: UUID, planned_at: datetime, equity: str) -> None:
    snapshot = EquitySnapshot(
        flow_id, planned_at, Decimal(100), Decimal(equity) - Decimal(100), Decimal(0), Decimal(0), Decimal(0)
    )
    platform.equity_snapshots.snapshots[platform.tenant_of("anna"), flow_id, planned_at] = snapshot
