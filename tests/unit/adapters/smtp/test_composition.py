"""The mail service of the installation: without its host no email leaves, and the API never reads its password (ADR
canale-email-delle-notifiche-con-smtp).
"""

import logging
from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.smtp.composition import smtp_adapters, smtp_service_adapters
from autotrading.adapters.outbound.smtp.configuration import _settings_of, _SmtpSettings
from autotrading.adapters.outbound.smtp.mailer import SmtpDisabledMailerAdapter, SmtpMailerAdapter

SERVICE = {"SMTP_HOST": "smtp.example", "SMTP_SENDER": "notifiche@autotrading.example"}


def _with_password(tmp_path: Path, values: dict[str, str]) -> ConfigurationSource:
    location = tmp_path / "smtp_password"
    location.write_text("PASSWORD-FAKE\n", encoding="utf-8")
    return ConfigurationSource({**values, "SMTP_PASSWORD_FILE": str(location)})


def test_without_a_host_the_mailer_is_the_disabled_one_and_the_service_is_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        mailer, service = smtp_adapters(ConfigurationSource({}))

    assert isinstance(mailer, SmtpDisabledMailerAdapter)
    assert not service.is_configured()
    assert "servizio di posta non configurato" in caplog.text


def test_with_a_host_and_a_sender_the_mailer_talks_to_the_mail_service() -> None:
    mailer, service = smtp_adapters(ConfigurationSource(SERVICE))

    assert isinstance(mailer, SmtpMailerAdapter)
    assert service.is_configured()


@pytest.mark.parametrize(("values", "configured"), [({}, False), (SERVICE, True)])
def test_the_api_learns_whether_the_service_exists_from_its_plain_settings(
    values: dict[str, str], configured: bool
) -> None:
    assert smtp_service_adapters(ConfigurationSource(values)).is_configured() is configured


def test_the_settings_default_to_the_submission_port_and_log_in_with_the_mounted_password(tmp_path: Path) -> None:
    settings = _settings_of(_with_password(tmp_path, {**SERVICE, "SMTP_USERNAME": "notifiche"}))

    assert (settings.host, settings.port, settings.sender) == ("smtp.example", 587, "notifiche@autotrading.example")
    assert settings.login == ("notifiche", "PASSWORD-FAKE")


def test_without_a_user_there_is_no_login() -> None:
    assert _settings_of(ConfigurationSource({**SERVICE, "SMTP_PORT": "465"})).login is None


def test_a_host_without_a_sender_is_missing_configuration() -> None:
    with pytest.raises(MissingConfigurationError, match="SMTP_SENDER"):
        smtp_adapters(ConfigurationSource({"SMTP_HOST": "smtp.example"}))


def test_a_user_without_the_password_file_is_missing_configuration() -> None:
    with pytest.raises(MissingConfigurationError, match="SMTP_PASSWORD_FILE"):
        smtp_adapters(ConfigurationSource({**SERVICE, "SMTP_USERNAME": "notifiche"}))


@pytest.mark.parametrize("port", ["0", "65536", "abc", "-1"])
def test_a_port_out_of_range_is_invalid_configuration(port: str) -> None:
    with pytest.raises(InvalidConfigurationError, match="SMTP_PORT"):
        smtp_adapters(ConfigurationSource({**SERVICE, "SMTP_PORT": port}))


def test_the_password_never_appears_in_the_settings_repr() -> None:
    settings = _SmtpSettings("smtp.example", 587, "s@x.it", ("notifiche", "PASSWORD-FAKE"))

    assert "PASSWORD-FAKE" not in repr(settings)
