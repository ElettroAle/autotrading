from autotrading.domain.flows.closed_position_page import CLOSED_POSITIONS_PER_PAGE, ClosedPositionPage


def test_a_page_holds_fifty_closed_positions() -> None:
    assert CLOSED_POSITIONS_PER_PAGE == 50


def test_a_page_keeps_its_number_its_positions_whether_another_follows_and_the_total() -> None:
    page = ClosedPositionPage(2, (), has_next=False, total=50)

    assert (page.number, page.positions, page.has_next, page.total) == (2, (), False, 50)
