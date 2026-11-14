from autotrading.domain.flows.closed_position_page import CLOSED_POSITIONS_PER_PAGE, ClosedPositionPage


def test_a_page_holds_fifty_closed_positions() -> None:
    assert CLOSED_POSITIONS_PER_PAGE == 50


def test_a_page_keeps_its_number_its_positions_and_whether_another_follows() -> None:
    page = ClosedPositionPage(2, (), has_next=False)

    assert (page.number, page.positions, page.has_next) == (2, (), False)
