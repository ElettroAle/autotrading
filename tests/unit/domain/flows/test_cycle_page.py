import pytest

from autotrading.domain.flows.cycle_page import CYCLES_PER_PAGE, PageNumber
from autotrading.domain.flows.errors import InvalidPageNumberError


def test_a_page_holds_fifty_cycles() -> None:
    assert CYCLES_PER_PAGE == 50


@pytest.mark.parametrize(("page", "offset"), [(1, 0), (2, 50), (3, 100)])
def test_a_page_starts_after_the_cycles_of_the_pages_before(page: int, offset: int) -> None:
    assert PageNumber(page).offset == offset


@pytest.mark.parametrize("page", [0, -1])
def test_the_pages_start_from_one(page: int) -> None:
    with pytest.raises(InvalidPageNumberError) as raised:
        PageNumber(page)

    assert raised.value.status_code == 400
    assert str(raised.value) == "numero di pagina non valido: le pagine partono da 1"
