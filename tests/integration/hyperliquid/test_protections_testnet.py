"""The protections adapter against the testnet: the lookup by client order id is public, a fresh address is enough."""

from decimal import Decimal

import pytest
from eth_account import Account as EthereumAccount

from autotrading.adapters.outbound.hyperliquid.exchange import ACCOUNT_ADDRESS
from autotrading.adapters.outbound.hyperliquid.protections import HyperliquidProtectionExchangeAdapter
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.trading_access import TradingAccess

pytestmark = pytest.mark.integration


# ADR-protezioni-ritentate-nel-ciclo: a protection the exchange never got is not found, so it goes again.
def test_a_protection_never_placed_is_not_found_by_its_client_order_id() -> None:
    access = TradingAccess("Hyperliquid Testnet", {ACCOUNT_ADDRESS: EthereumAccount.create().address})
    stop = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, Decimal(57000))

    assert HyperliquidProtectionExchangeAdapter.for_network(testnet=True).find(access, stop) is None
