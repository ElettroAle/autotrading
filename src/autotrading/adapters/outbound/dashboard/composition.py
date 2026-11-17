from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.dashboard.configuration import _settings_of
from autotrading.adapters.outbound.dashboard.notification_links import DashboardNotificationLinkAdapter


def dashboard_adapters(source: ConfigurationSource) -> DashboardNotificationLinkAdapter:
    """The pages of the dashboard the notifications lead to (ADR destinazioni-delle-notifiche-nella-dashboard)."""
    return DashboardNotificationLinkAdapter(_settings_of(source).url)
