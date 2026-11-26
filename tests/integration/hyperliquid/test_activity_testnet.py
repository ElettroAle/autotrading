"""The activity adapter against the testnet: the readings are public, so a fresh address is enough."""

from decimal import Decimal

import pytest
from eth_account import Account as EthereumAccount

from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.exchange import ACCOUNT_ADDRESS
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.statistics_period import TimeWindow

pytestmark = pytest.mark.integration


def test_a_fresh_address_has_an_empty_activity_in_usdc() -> None:
    reference = AccountReference({ACCOUNT_ADDRESS: EthereumAccount.create().address})

    activity = HyperliquidAccountActivityAdapter.for_network(testnet=True).activity(reference)

    assert (activity.currency, activity.balance, activity.available_margin) == ("USDC", Decimal(0), Decimal(0))
    assert activity.positions == ()


def test_a_fresh_address_has_no_deposit_nor_withdrawal() -> None:
    # R3.4.2, ADR storico-delle-variazioni-di-capitale: the transfers are read on the address alone.
    reference = AccountReference({ACCOUNT_ADDRESS: EthereumAccount.create().address})

    transfers = HyperliquidAccountActivityAdapter.for_network(testnet=True).transfers(reference, TimeWindow())

    assert transfers == ()


def test_a_fresh_address_pays_a_fee_on_the_value_of_a_market_order() -> None:
    # R5.5.6, ADR costo-di-andata-e-ritorno-nel-contesto-dell-agente: the fee is read on the address alone.
    reference = AccountReference({ACCOUNT_ADDRESS: EthereumAccount.create().address})

    rate = HyperliquidAccountActivityAdapter.for_network(testnet=True).market_order_fee_rate(reference)

    assert Decimal(0) < rate < Decimal("0.01")
