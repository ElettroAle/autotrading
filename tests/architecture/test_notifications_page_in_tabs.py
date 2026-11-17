"""ADR-pagina-notifiche-a-schede: the page of the notifications in two tabs of the shared ViewTabs, the channels in
boxes of one shape, the mail server panel grown from the shared components on the generated client of the API, all
inside the feature of the notifications.
"""

import re
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src"
FEATURE = DASHBOARD / "features" / "notifications"
COMPONENTS = FEATURE / "components"
ROUTE = DASHBOARD / "app" / "routes" / "app" / "notifications.tsx"
API_MODULES = ("get-mail-server.ts", "set-mail-server.ts", "remove-mail-server.ts")
SHARED_COMPONENTS = {
    "notifications-view.tsx": ("@/components/ui/view-tabs",),
    "mail-server-panel.tsx": (
        "@/components/ui/command-button",
        "@/components/ui/confirmation-dialog",
        "@/components/ui/form/input-field",
        "@/components/ui/form/select-field",
    ),
    "channel-box.tsx": ("@/components/ui/icons/icon",),
}
OWN_CONTROLS = re.compile(r"<(button|table)[\s>]")
OTHER_FEATURES = re.compile(r"from '@/features/(?!notifications/)")


def own_controls_in(source: str) -> list[str]:
    """The controls a module draws itself instead of taking the shared ones."""
    return OWN_CONTROLS.findall(source)


def test_adr_pagina_notifiche_a_schede_the_route_shows_the_view_in_tabs() -> None:
    route = ROUTE.read_text(encoding="utf-8")

    assert "from '@/features/notifications/components/notifications-view'" in route
    assert "<NotificationsView />" in route


@pytest.mark.parametrize(("module", "imports"), SHARED_COMPONENTS.items())
def test_adr_pagina_notifiche_a_schede_the_page_grows_from_the_shared_components(
    module: str, imports: tuple[str, ...]
) -> None:
    source = (COMPONENTS / module).read_text(encoding="utf-8")

    assert all(f"from '{shared}'" in source for shared in imports), imports
    assert own_controls_in(source) == []
    assert OTHER_FEATURES.search(source) is None


def test_adr_pagina_notifiche_a_schede_every_channel_has_the_same_box() -> None:
    boxes = (COMPONENTS / "notification-channel-boxes.tsx").read_text(encoding="utf-8")

    assert boxes.count("<ChannelBox ") == 2
    assert "md:grid-cols-2" in boxes


def test_adr_pagina_notifiche_a_schede_the_mail_server_is_read_on_the_generated_client() -> None:
    schema = (DASHBOARD / "lib" / "api-schema.d.ts").read_text(encoding="utf-8")

    assert '"/notifications/mail-server": {' in schema
    for module in API_MODULES:
        source = (FEATURE / "api" / module).read_text(encoding="utf-8")
        assert "'/notifications/mail-server'" in source, module


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ('<button type="button" onClick={save}>Salva</button>', ["button"]),
        ("<table>\n<tr /></table>", ["table"]),
        ('<CommandButton tone="primary">Salva</CommandButton>', []),
    ],
)
def test_adr_pagina_notifiche_a_schede_a_control_drawn_by_the_module_is_found(source: str, found: list[str]) -> None:
    assert own_controls_in(source) == found
