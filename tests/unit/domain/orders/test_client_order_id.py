from uuid import UUID

from autotrading.domain.orders.client_order_id import ClientOrderId


def test_each_new_identifier_is_different() -> None:
    assert ClientOrderId.new() != ClientOrderId.new()


def test_the_hex_form_is_the_128_bits_the_exchange_expects() -> None:
    order_id = ClientOrderId(UUID("0123456789abcdef0123456789abcdef"))

    assert order_id.hex == "0x0123456789abcdef0123456789abcdef"
