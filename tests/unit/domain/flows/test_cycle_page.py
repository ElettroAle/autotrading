from autotrading.domain.flows.cycle_page import CYCLES_PER_PAGE


def test_a_page_holds_fifty_cycles() -> None:
    assert CYCLES_PER_PAGE == 50
