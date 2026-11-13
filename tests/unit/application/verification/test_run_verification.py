from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.application.verification.run_verification import RunVerificationCommand, RunVerificationUseCase
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.verification_run import VerificationRun
from tests.support.verification import a_run, passed_steps

ANNA = UserId("oid-anna")


class RecordingVerification:
    def __init__(self) -> None:
        self.requests: list[tuple[UUID, UserId, Decimal | None]] = []
        self.answer = a_run(*passed_steps())

    def run(self, account_id: UUID, user_id: UserId, amount: Decimal | None) -> VerificationRun:
        self.requests.append((account_id, user_id, amount))
        return self.answer


def test_the_worker_is_asked_to_run_the_procedure_for_the_user_who_launched_it() -> None:
    verification, account_id = RecordingVerification(), uuid4()

    run = RunVerificationUseCase(verification).execute(RunVerificationCommand(account_id, ANNA))

    assert verification.requests == [(account_id, ANNA, None)]
    assert run is verification.answer


def test_the_worker_is_asked_for_the_amount_the_user_chose() -> None:
    verification, account_id = RecordingVerification(), uuid4()

    RunVerificationUseCase(verification).execute(RunVerificationCommand(account_id, ANNA, Decimal("20.5")))

    assert verification.requests == [(account_id, ANNA, Decimal("20.5"))]
