"""ADR-sorveglianza-del-prezzo-per-lo-stop-che-segue: the domain computes the stop; a periodic job of one minute in
apscheduler/ runs a use case of the flows context that reads the price only for the flows with the setting, skips a flow
whose cycle runs with the same lock of the cycles and moves the stop through the existing replacement of the orders
context; the best price lives in a table under RLS; the risk check brings back a farther stop of the agent.
"""

import ast
import inspect
from datetime import timedelta
from pathlib import Path
from typing import get_type_hints

from autotrading import bootstrap
from autotrading.adapters.outbound.apscheduler import periodic_check_scheduler
from autotrading.application.flows import follow_trailing_stops, schedule_trailing_stop_checks
from autotrading.application.flows import ports as flow_ports
from autotrading.application.flows.follow_trailing_stops import FollowTrailingStopsUseCase, StopMoves
from autotrading.application.orders.move_flow_stop import MoveFlowStopUseCase
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.domain.flows import risk_check
from autotrading.domain.flows.trailing_stop import TrailingStop

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0060_flow_watched_positions.py"
SCHEDULER_LIBRARY = "apscheduler"


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    return imported | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}


def _schedulers_outside_the_folder(sources: dict[str, str]) -> list[str]:
    """The modules that run the periodic check with a scheduler library themselves."""
    return sorted(
        name
        for name, source in sources.items()
        if any(module.split(".")[0] == SCHEDULER_LIBRARY for module in _imported_modules(source))
    )


def test_adr_sorveglianza_del_prezzo_the_domain_computes_the_stop() -> None:
    assert callable(TrailingStop.moved_stop)
    assert "moved_stop" in inspect.getsource(follow_trailing_stops)


def test_adr_sorveglianza_del_prezzo_the_job_of_one_minute_is_in_the_apscheduler_folder() -> None:
    every = schedule_trailing_stop_checks.TRAILING_STOP_CHECK_EVERY

    assert every == timedelta(minutes=1)
    assert "IntervalTrigger" in inspect.getsource(periodic_check_scheduler)
    sources = {
        module.__name__: inspect.getsource(module) for module in (follow_trailing_stops, schedule_trailing_stop_checks)
    }

    assert _schedulers_outside_the_folder(sources) == []


def test_adr_sorveglianza_del_prezzo_a_scheduler_in_the_use_case_is_found() -> None:
    use_case = "from apscheduler.triggers.interval import IntervalTrigger\n"

    assert _schedulers_outside_the_folder({"follow_trailing_stops": use_case}) == ["follow_trailing_stops"]


def test_adr_sorveglianza_del_prezzo_only_flows_with_the_setting_are_read_and_a_running_cycle_is_skipped() -> None:
    hints = get_type_hints(FollowTrailingStopsUseCase.__init__)
    execute = inspect.getsource(FollowTrailingStopsUseCase.execute)

    assert hints["lock"] is flow_ports.FlowLockPort
    assert "trailing_stop.active" in execute
    assert "_cycle_not_running" in execute
    follow = inspect.getsource(bootstrap.follow_trailing_stops)
    assert "SqlAlchemyFlowLockAdapter(engine)" in follow


def test_adr_sorveglianza_del_prezzo_the_stop_moves_through_the_replacement_of_the_orders_context() -> None:
    assert get_type_hints(StopMoves)["move"] is flow_ports.FlowStopMovePort
    assert get_type_hints(MoveFlowStopUseCase.__init__)["update"] is UpdateFlowProtectionUseCase
    assert "MoveFlowStopUseCase(" in inspect.getsource(bootstrap.follow_trailing_stops)


def test_adr_sorveglianza_del_prezzo_the_best_price_lives_in_a_table_under_rls() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")

    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY flow_watched_positions_of_tenant" in migration


def test_adr_sorveglianza_del_prezzo_the_risk_check_brings_back_a_farther_stop_of_the_agent() -> None:
    assert "oltre lo stop che segue il prezzo" in inspect.getsource(risk_check)
