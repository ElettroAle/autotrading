from autotrading.application.sources.record_source_credentials_rejection import (
    RecordSourceCredentialsRejectionUseCase,
)
from tests.fakes.source_credentials import (
    FakeSourceCredentialsRejectionNoticeAdapter,
)
from tests.support.source_keys import PAID, REJECTED_AT, TODAY, Keys


def test_a_refusal_is_recorded_and_told_only_the_first_time() -> None:
    keys = Keys()
    keys.configure_paid()
    notice = FakeSourceCredentialsRejectionNoticeAdapter()
    record = RecordSourceCredentialsRejectionUseCase(keys.credentials, notice)

    record.execute(PAID, REJECTED_AT)
    record.execute(PAID, TODAY)

    saved = keys.credentials.get(PAID)
    assert saved is not None
    assert (saved.rejected_at, notice.told) == (REJECTED_AT, [PAID])
