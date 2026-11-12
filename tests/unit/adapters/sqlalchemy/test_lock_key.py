from uuid import UUID

from autotrading.adapters.outbound.sqlalchemy.scheduling import lock_key


def test_the_lock_of_a_flow_is_the_signed_bigint_of_the_first_half_of_its_id() -> None:
    assert lock_key(UUID("00000000-0000-0001-ffff-ffffffffffff")) == 1
    assert lock_key(UUID("ffffffff-ffff-ffff-0000-000000000000")) == -1
    assert lock_key(UUID("7fffffff-ffff-ffff-0000-000000000000")) == 2**63 - 1
