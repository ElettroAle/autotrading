"""ADR-ciclo-su-richiesta-nel-worker, ADR-comando-del-ciclo-su-richiesta-nell-api and
ADR-pulsante-esegui-ora-nella-pagina-del-flusso: the worker runs the cycle asked for now with the same use case as the
planned ones, recording what started it; the API asks the worker for it through a port of the flows realised only by
the worker adapter, with its own timeout, and answers 201 with the cycle; the dashboard sends it from the commands of
the flow, with the shared look of a command and the shared refusal.
"""

import inspect
import json
import re
from pathlib import Path
from typing import get_type_hints

from fastapi.routing import APIRoute

from autotrading.adapters.inbound.api.cycles import CycleDetailResponse, CycleSummaryResponse
from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker import on_demand_cycle
from autotrading.adapters.outbound.worker.on_demand_cycle import WorkerOnDemandCycleAdapter
from autotrading.application.flows import run_cycle_on_demand
from autotrading.application.flows.errors import CycleInProgressError, CycleWorkerUnavailableError, FlowNotActiveError
from autotrading.application.flows.ports import OnDemandCyclePort
from autotrading.application.flows.request_on_demand_cycle import RequestOnDemandCycleUseCase
from autotrading.application.flows.run_cycle import RunCycleCommand
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from tests.support.worker import TOKEN, Worker

REPOSITORY = Path(__file__).resolve().parents[2]
SOURCE = REPOSITORY / "src" / "autotrading"
MIGRATIONS = REPOSITORY / "migrations" / "versions"
DASHBOARD = REPOSITORY / "dashboard"
WORKER_ROUTE = "/tenants/{tenant_id}/flows/{flow_id}/cycles"
API_ROUTE = "/flows/{flow_id}/cycles"
# The longest step of a cycle: the call to the model (R1.4.6).
MODEL_TIMEOUT_SECONDS = 120


def realisations_of(method: str) -> list[Path]:
    return [
        path
        for path in (SOURCE / "adapters").rglob("*.py")
        if re.search(rf"^    def {method}\(self, flow_id: UUID\) -> CycleRecord:", path.read_text("utf-8"), re.M)
    ]


def test_adr_ciclo_su_richiesta_nel_worker_the_same_use_case_runs_it_and_records_what_started_it() -> None:
    worker_routes = [
        route for route in create_worker_api(TOKEN, Worker().for_tenant).routes if isinstance(route, APIRoute)
    ]
    on_demand_source = inspect.getsource(run_cycle_on_demand)
    migration = next(MIGRATIONS.glob("*_cycle_trigger.py")).read_text(encoding="utf-8")

    assert {trigger.value for trigger in CycleTrigger} == {"scheduled", "on_demand"}
    assert get_type_hints(RunCycleCommand)["trigger"] is CycleTrigger
    assert get_type_hints(CycleRecord)["trigger"] is CycleTrigger
    assert "CycleTrigger.ON_DEMAND" in on_demand_source
    assert "RunCycleCommand(" in on_demand_source
    assert "cycle_graph" not in on_demand_source
    assert "PlannedCycle" not in on_demand_source
    assert any(route.path == WORKER_ROUTE and route.methods == {"POST"} for route in worker_routes)
    assert "cycles_trigger_known" in migration
    assert "server_default" in migration


def test_adr_comando_del_ciclo_su_richiesta_nell_api_only_the_worker_adapter_asks_with_its_own_timeout() -> None:
    document = json.loads((DASHBOARD / "openapi.json").read_text(encoding="utf-8"))
    answers = document["paths"][API_ROUTE]["post"]["responses"]
    adapter_source = inspect.getsource(on_demand_cycle)

    assert OnDemandCyclePort.__module__ == "autotrading.application.flows.ports"
    assert get_type_hints(RequestOnDemandCycleUseCase.__init__)["cycles"] is OnDemandCyclePort
    assert realisations_of("run") == [SOURCE / "adapters" / "outbound" / "worker" / "on_demand_cycle.py"]
    assert WorkerOnDemandCycleAdapter.__module__ == on_demand_cycle.__name__
    assert on_demand_cycle.TIMEOUT_SECONDS > MODEL_TIMEOUT_SECONDS
    assert "timeout=TIMEOUT_SECONDS" in adapter_source
    assert (FlowNotActiveError.status_code, CycleInProgressError.status_code) == (409, 409)
    assert CycleWorkerUnavailableError.status_code == 503
    assert answers["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CycleSummaryResponse"
    }
    assert "trigger" in CycleSummaryResponse.model_fields
    assert "trigger" in CycleDetailResponse.model_fields


def test_adr_pulsante_esegui_ora_nella_pagina_del_flusso_the_command_lives_with_the_commands_of_the_flow() -> None:
    feature = DASHBOARD / "src" / "features" / "flow-commands"
    mutation = (feature / "api" / "run-cycle-now.ts").read_text(encoding="utf-8")
    commands = (feature / "components" / "flow-commands.tsx").read_text(encoding="utf-8")
    schema = (DASHBOARD / "src" / "lib" / "api-schema.d.ts").read_text(encoding="utf-8")

    assert f"api.POST('{API_ROUTE}'" in mutation
    assert "invalidateQueries" in mutation
    assert "from '@/components/ui/command-refusal'" in commands
    assert re.search(r"<CommandButton\s+tone=\"secondary\"\s+icon=\"refresh\"\s+onClick=\{\(\) => cycleNow\.mutate\(\)\}", commands)
    assert "Ciclo in corso…" in commands
    assert not (DASHBOARD / "src" / "features" / "flows" / "components" / "command-refusal.tsx").exists()
    for response in (CycleSummaryResponse, CycleDetailResponse):
        block = re.search(rf"{response.__name__}: \{{(.*?)\n        \}};", schema, re.DOTALL)
        assert block is not None
        assert "trigger: string;" in block.group(1)
