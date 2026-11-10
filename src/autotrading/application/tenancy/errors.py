from autotrading.application.errors import ApplicationError
from autotrading.domain.tenancy.user_id import UserId


class TenantAlreadyExistsError(ApplicationError):
    def __init__(self, user_id: UserId) -> None:
        super().__init__("il tenant dell'utente esiste già")
        self.user_id = user_id


class CrossTenantAccessError(ApplicationError):
    """A tenant-bound adapter received an entity of another tenant (rule context-tenancy)."""

    def __init__(self) -> None:
        super().__init__("non trovato")
