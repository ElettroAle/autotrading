from decimal import Decimal

import pytest

from autotrading.domain.flows.errors import InvalidDefaultStopLossError, InvalidDefaultTakeProfitError
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from tests.support.flows import a_configuration


def test_a_flow_without_defaults_has_a_stop_loss_of_five_percent_and_no_take_profit() -> None:
    defaults = ProtectionDefaults()

    assert (defaults.stop_loss_percent, defaults.take_profit_percent) == (Decimal(5), None)


@pytest.mark.parametrize("percent", [Decimal("0.1"), Decimal(3), Decimal(50)])
def test_accepts_a_default_stop_loss_from_a_tenth_to_fifty(percent: Decimal) -> None:
    assert ProtectionDefaults(percent).stop_loss_percent == percent


@pytest.mark.parametrize("percent", [Decimal(0), Decimal("0.05"), Decimal(51), Decimal("NaN"), Decimal("Infinity")])
def test_refuses_a_default_stop_loss_out_of_range_naming_the_setting(percent: Decimal) -> None:
    with pytest.raises(InvalidDefaultStopLossError, match="lo stop loss predefinito va da 0,1 a 50") as refused:
        ProtectionDefaults(percent)

    assert refused.value.setting is FlowSetting.DEFAULT_STOP_LOSS
    assert refused.value.details == {"field": "default_stop_loss_percent"}


@pytest.mark.parametrize("percent", [Decimal("0.01"), Decimal(10), Decimal(200)])
def test_accepts_any_positive_default_take_profit(percent: Decimal) -> None:
    assert ProtectionDefaults(take_profit_percent=percent).take_profit_percent == percent


@pytest.mark.parametrize("percent", [Decimal(0), Decimal(-1), Decimal("NaN"), Decimal("Infinity")])
def test_refuses_a_default_take_profit_not_positive_naming_the_setting(percent: Decimal) -> None:
    with pytest.raises(InvalidDefaultTakeProfitError, match="il take profit predefinito è maggiore di 0") as refused:
        ProtectionDefaults(take_profit_percent=percent)

    assert refused.value.setting is FlowSetting.DEFAULT_TAKE_PROFIT


def test_every_configuration_has_the_defaults_unless_it_says_otherwise() -> None:
    assert a_configuration().protection_defaults == ProtectionDefaults()
