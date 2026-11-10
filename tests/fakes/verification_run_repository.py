from autotrading.domain.verification.verification_run import VerificationRun


class InMemoryVerificationRunRepositoryAdapter:
    """The runs of the procedure of one tenant, as the database records them."""

    def __init__(self) -> None:
        self.runs: list[VerificationRun] = []

    def add(self, run: VerificationRun) -> None:
        self.runs.append(run)
