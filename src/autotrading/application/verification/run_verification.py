from dataclasses import dataclass
from uuid import UUID

from autotrading.application.verification.ports import VerificationPort
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.verification_run import VerificationRun


@dataclass(frozen=True, slots=True)
class RunVerificationCommand:
    account_id: UUID
    user_id: UserId


class RunVerificationUseCase:
    """A user launches the procedure of verification on an account of the tenant (R0.4.1, ADR 0024).

    The worker holds the credentials and checks, under row level security, that the account belongs to the tenant.
    """

    def __init__(self, verification: VerificationPort) -> None:
        self._verification = verification

    def execute(self, command: RunVerificationCommand) -> VerificationRun:
        return self._verification.run(command.account_id, command.user_id)
