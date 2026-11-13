import os
from collections.abc import Mapping
from pathlib import Path

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.domain.accounts.installation_environment import InstallationEnvironment

ENVIRONMENT = "APP_ENVIRONMENT"
FILE_SUFFIX = "_FILE"
# The live environment of the process, not a copy: the only place the platform reads it.
PROCESS_ENVIRONMENT: Mapping[str, str] = os.environ


class ConfigurationSource:
    """What the installation declares to a service: plain values in variables, secrets in read-only mounted files
    whose path the variable <NAME>_FILE gives (ADR 0015). Each adapter folder reads here its own settings.
    """

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def value(self, name: str) -> str:
        value = self.optional(name)
        if value is None:
            raise MissingConfigurationError(name)
        return value

    def optional(self, name: str) -> str | None:
        return self._values.get(name, "").strip() or None

    def secret(self, name: str) -> str:
        variable = name + FILE_SUFFIX
        secret = self._file_content(self.value(variable))
        if secret is None:
            raise MissingConfigurationError(variable)
        return secret

    def optional_secret(self, name: str) -> str | None:
        location = self.optional(name + FILE_SUFFIX)
        if location is None:
            return None
        return self._file_content(location)

    def environment(self) -> InstallationEnvironment:
        """Which installation this is: declared once for the whole service, as the host declares it in .NET."""
        return InstallationEnvironment.declared(self.optional(ENVIRONMENT))

    @staticmethod
    def _file_content(location: str) -> str | None:
        path = Path(location)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8").strip() or None
