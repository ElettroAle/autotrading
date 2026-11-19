from dataclasses import dataclass

from autotrading.application.sources.ports import SourceCredentialsRepositoryPort


@dataclass(frozen=True, slots=True)
class RemoveSourceCredentialsCommand:
    adapter: str


class RemoveSourceCredentialsUseCase:
    """Forgets the credentials of an adapter: it is no longer activatable, and an absent source in the cycles of the
    flows that chose it (R4.1.2)."""

    def __init__(self, credentials: SourceCredentialsRepositoryPort) -> None:
        self._credentials = credentials

    def execute(self, command: RemoveSourceCredentialsCommand) -> None:
        self._credentials.remove(command.adapter)
