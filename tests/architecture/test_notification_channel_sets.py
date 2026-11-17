"""ADR-canali-delle-notifiche-come-insieme: the choice of a type of event is a set of channels, never a combination of
them. The domain lists only channels and chooses sets of them, the use cases deliver each channel by itself, the table
keeps an array of known channels and the API reads and writes lists of channels.
"""

import ast
import re
import typing
from pathlib import Path

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.notifications.choose_notification_channel import ChooseNotificationChannelCommand
from autotrading.application.notifications.set_flow_channel_exception import SetFlowChannelExceptionCommand
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.notification_channel import NotificationChannel
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.architecture import SOURCE_ROOT
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
CHANNEL_MODULE = Path(SOURCE_ROOT) / "domain" / "notifications" / "notification_channel.py"
SET_OF_CHANNELS = frozenset[NotificationChannel]
# The words a member takes when it stands for several channels, or for none of them.
COMBINATION_WORDS = ("BOTH", "ALL", "NONE", "NEITHER", "ANY", "_AND_")

COMBINATIONS = """
class NotificationChannel(StrEnum):
    TELEGRAM = "chat"
    EMAIL = "email"
    BOTH = "both"
    NONE = "none"
"""
CHANNELS = """
class NotificationChannel(StrEnum):
    TELEGRAM = "chat"
    EMAIL = "email"
"""


def combination_members(source: str) -> list[str]:
    """The members of the enum of the channels that stand for several channels or for none."""
    tree = ast.parse(source)
    enum = next(
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "NotificationChannel"
    )
    members = [
        target.id
        for node in enum.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ]
    return [member for member in members if any(word in member for word in COMBINATION_WORDS)]


def test_adr_canali_delle_notifiche_come_insieme_the_enum_lists_channels_never_combinations() -> None:
    assert combination_members(CHANNEL_MODULE.read_text(encoding="utf-8")) == []


def test_adr_canali_delle_notifiche_come_insieme_a_member_for_a_combination_is_found() -> None:
    assert combination_members(COMBINATIONS) == ["BOTH", "NONE"]
    assert combination_members(CHANNELS) == []


def test_adr_canali_delle_notifiche_come_insieme_the_choices_are_sets_of_channels() -> None:
    channels_for = typing.get_type_hints(ChannelPreferences.channels_for)["return"]
    choose = typing.get_type_hints(ChooseNotificationChannelCommand)["channels"]
    excepting = typing.get_type_hints(SetFlowChannelExceptionCommand)["channels"]

    assert [hint.__value__ for hint in (channels_for, choose, excepting)] == [SET_OF_CHANNELS] * 3


def test_adr_canali_delle_notifiche_come_insieme_the_table_keeps_an_array_of_known_channels() -> None:
    migration = next(MIGRATIONS.glob("*_notification_channel_sets.py")).read_text(encoding="utf-8")

    assert "ADD COLUMN channels text[]" in migration
    assert "CHECK (channels <@ {KNOWN_CHANNELS})" in migration
    upgrade = migration.split("def downgrade")[0]
    assert re.search(r"DROP COLUMN channel\b", upgrade)


def test_adr_canali_delle_notifiche_come_insieme_the_api_reads_and_writes_lists_of_channels() -> None:
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(InMemoryTenantRepositoryAdapter()),
        Platform().for_tenant,
        IdentityProvider().authentication(),
    )
    schemas = api.openapi()["components"]["schemas"]

    for name in ("ChannelChoiceRequest", "FlowChannelRequest", "EventChannelResponse"):
        properties = schemas[name]["properties"]
        assert "channel" not in properties, name
        assert properties["channels"]["type"] == "array", name
    assert schemas["ChannelStateResponse"]["properties"]["configured"]["type"] == "boolean"
