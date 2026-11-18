"""Which cases no flow explains are told to the user (R1.6.2, ADR variazioni-sotto-soglia-senza-notifica)."""

import pytest

from autotrading.domain.flows.unattributable import UnattributableKind


@pytest.mark.parametrize("kind", [UnattributableKind.POSITION, UnattributableKind.FILL])
def test_a_position_or_an_execution_is_told(kind: UnattributableKind) -> None:
    assert kind.told


def test_a_change_of_the_balance_within_the_threshold_is_recorded_without_being_told() -> None:
    assert not UnattributableKind.BALANCE_CHANGE.told
