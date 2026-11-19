from dataclasses import dataclass
from datetime import date
from uuid import UUID

from autotrading.domain.flows.flow import Flow


@dataclass(frozen=True, slots=True)
class FlowKey:
    """A key flows use, with its expiry: the credentials of an account, for every flow of the account, or the key of a
    provider, for every flow on a model of the provider (R6.2.2). Its name is the one the user knows it by.

    The day of the expiry is already expired: the key works until the day before, as the notices tell.
    """

    name: str
    expires_on: date
    account_id: UUID | None = None
    provider: str | None = None

    def is_expired_on(self, today: date) -> bool:
        return self.expires_on <= today

    def used_by(self, flow: Flow) -> bool:
        return flow.account_id == self.account_id or flow.model_provider == self.provider

    @property
    def pause_reason(self) -> str:
        return f"chiave {self.name} scaduta"
