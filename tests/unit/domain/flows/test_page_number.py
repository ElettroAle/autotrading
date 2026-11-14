import pytest

from autotrading.domain.flows.errors import InvalidPageNumberError
from autotrading.domain.flows.page_number import PageNumber


@pytest.mark.parametrize(("page", "offset"), [(1, 0), (2, 50), (3, 100)])
def test_a_page_starts_after_the_items_of_the_pages_before(page: int, offset: int) -> None:
    assert PageNumber(page).offset(50) == offset


def test_the_offset_follows_the_size_of_the_pages() -> None:
    assert PageNumber(3).offset(20) == 40


@pytest.mark.parametrize("page", [0, -1])
def test_the_pages_start_from_one(page: int) -> None:
    with pytest.raises(InvalidPageNumberError) as raised:
        PageNumber(page)

    assert raised.value.status_code == 400
    assert str(raised.value) == "numero di pagina non valido: le pagine partono da 1"
