"""ADR-scelta-dei-canali-nella-dashboard: the channels of the notifications show in the shared components of the
dashboard, on the generated client of the API.
"""

from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src"
PANEL = DASHBOARD / "features" / "notifications" / "components" / "notification-channels-panel.tsx"


def test_adr_scelta_dei_canali_nella_dashboard_the_section_grows_from_the_shared_components() -> None:
    panel = PANEL.read_text(encoding="utf-8")
    schema = (DASHBOARD / "lib" / "api-schema.d.ts").read_text(encoding="utf-8")

    assert "from '@/components/ui/data-table'" in panel
    assert "from '@/components/ui/form/select-field'" in panel
    assert "<table" not in panel
    assert '"/notifications/channels": {' in schema
    assert '"/notifications/channels/flows/{flow_id}/{event}": {' in schema
