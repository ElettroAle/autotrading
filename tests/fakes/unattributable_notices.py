from uuid import UUID


class FakeUnattributableAssetNoticeAdapter:
    """Keeps the positions or the executions a use case tells, instead of sending them to the chat of the tenant, and
    the accounts they lead to (R3.5.6)."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str]] = []
        self.accounts: list[UUID] = []

    def execute(self, account_id: UUID, account_name: str, asset: str) -> None:
        self.told.append((account_name, asset))
        self.accounts.append(account_id)
