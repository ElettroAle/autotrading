from datetime import datetime

from autotrading.application.sources.ports import SourceCredentialsRejectionNoticePort, SourceCredentialsRepositoryPort


class RecordSourceCredentialsRejectionUseCase:
    """Keeps that the provider refused the credentials of an adapter and tells the tenant, once until the credentials
    are replaced (R4.1.2, ADR credenziali-degli-adapter-delle-fonti)."""

    def __init__(
        self, credentials: SourceCredentialsRepositoryPort, notice: SourceCredentialsRejectionNoticePort
    ) -> None:
        self._credentials = credentials
        self._notice = notice

    def execute(self, adapter: str, at: datetime) -> None:
        if not self._credentials.mark_rejected(adapter, at):
            return
        self._notice.execute(adapter)
