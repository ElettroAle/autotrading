"""ADR-avvisi-nel-contesto-delle-notifiche: an alert is a fact of the notifications, with no context of its own. The use
cases of the four events open the alert before they notify; the flows resolve it through a port of their own, which the
adapter of the alerts realizes in the folder of PostgreSQL, under row level security.
"""

import ast
import inspect
import re
from pathlib import Path

from autotrading.adapters.outbound.sqlalchemy.alert_repository import SqlAlchemyAlertRepositoryAdapter
from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusUseCase
from autotrading.application.flows.confirm_reconciliation import ConfirmReconciliationUseCase
from autotrading.application.flows.ports import AlertResolutionPort
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.stop_flow import StopFlowUseCase
from autotrading.application.notifications.ports import AlertRepositoryPort
from tests.support.architecture import SOURCE_ROOT, source_modules

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
NOTICES = (
    "notify_flow_paused.py",
    "notify_reconciliation_alarm.py",
    "notify_unattributable_fill.py",
    "notify_unattributable_position.py",
)
ALERT_CLASS = re.compile(r"^class Alert[:(]", re.MULTILINE)
RESOLVERS = (
    ArchiveFlowUseCase,
    ChangeFlowStatusUseCase,
    ConfirmReconciliationUseCase,
    ReconcileAccountUseCase,
    StopFlowUseCase,
)

# The notification leaves before its alert opens: its link could not lead to the alert.
NOTIFIED_FIRST = """
class NotifyFlowPausedUseCase:
    def execute(self, flow_id, flow_name, reason):
        self._notifier.execute(Notification.flow_paused(flow_id, flow_name, reason, None))
        self._alerts.open(AlertCause.flow_paused(flow_id, flow_name, reason))
"""
OPENED_FIRST = """
class NotifyFlowPausedUseCase:
    def execute(self, flow_id, flow_name, reason):
        alert_id = self._alerts.open(AlertCause.flow_paused(flow_id, flow_name, reason))
        self._notifier.execute(Notification.flow_paused(flow_id, flow_name, reason, alert_id.value))
"""


def opens_the_alert_before_notifying(source: str) -> bool:
    """Whether `execute` opens the alert, and only then hands the notification to the notifier."""
    execute = next(
        node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    calls = [
        (node.lineno, ast.unparse(node.func))
        for node in ast.walk(execute)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    opened = [line for line, name in calls if name == "self._alerts.open"]
    notified = [line for line, name in calls if name == "self._notifier.execute"]
    return bool(opened) and bool(notified) and max(opened) < min(notified)


def test_adr_avvisi_the_alert_lives_in_the_notifications_with_no_context_of_its_own() -> None:
    alert_modules = {module.path for module in source_modules() if ALERT_CLASS.search(module.text)}

    assert alert_modules == {"domain/notifications/alert.py"}
    assert not (Path(SOURCE_ROOT) / "domain" / "alerts").exists()
    assert not (Path(SOURCE_ROOT) / "application" / "alerts").exists()


def test_adr_avvisi_the_four_notices_open_the_alert_before_they_notify() -> None:
    folder = Path(SOURCE_ROOT) / "application" / "notifications"

    late = [name for name in NOTICES if not opens_the_alert_before_notifying((folder / name).read_text("utf-8"))]

    assert late == []


def test_adr_avvisi_a_notice_that_notifies_before_opening_is_found() -> None:
    assert not opens_the_alert_before_notifying(NOTIFIED_FIRST)
    assert opens_the_alert_before_notifying(OPENED_FIRST)


def test_adr_avvisi_the_flows_resolve_the_alerts_through_a_port_of_their_own() -> None:
    without = [
        resolver.__name__
        for resolver in RESOLVERS
        if AlertResolutionPort not in {parameter.annotation for parameter in _parameters_of(resolver)}
    ]

    assert without == []


def test_adr_avvisi_the_adapter_of_the_alerts_realizes_both_ports() -> None:
    required = _public_methods(AlertRepositoryPort) | _public_methods(AlertResolutionPort)

    assert required - _public_methods(SqlAlchemyAlertRepositoryAdapter) == set()


def test_adr_avvisi_the_alerts_belong_to_a_tenant_under_row_level_security() -> None:
    migration = next(MIGRATIONS.glob("*_alerts.py")).read_text(encoding="utf-8")

    assert "tenant_id" in migration
    assert "ALTER TABLE alerts FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY alerts_of_tenant ON alerts" in migration
    assert 'postgresql_where=sa.text("resolved_at IS NULL")' in migration


def _parameters_of(use_case: type) -> list[inspect.Parameter]:
    return list(inspect.signature(use_case, eval_str=True).parameters.values())


def _public_methods(kind: type) -> set[str]:
    return {name for name, _ in inspect.getmembers(kind, inspect.isfunction) if not name.startswith("_")}
