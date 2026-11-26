"""ADR-controllo-dell-esposizione-del-conto-nel-rischio: a type of the domain sums the exposure long and short of the
flows of the account, with a flow excluded on request; the risk check controls the account after the controls of the
flow, on the value that would be sent, and blocks beyond the limit without reducing; the openings of one cycle add up;
the cycle computes nothing more for an account without limit and a flow without the option.
"""

import inspect
import re

from autotrading.application.flows.read_cycle_flow import ReadCycleFlowUseCase
from autotrading.domain.flows import account_exposure, account_exposure_reading
from autotrading.domain.flows.risk_check import RiskCheck, RiskState

# A reduction of the opening to the limit of the account: beyond it the opening is blocked, never reduced.
REDUCTION = re.compile(r"Adjustment\(|\.adjusted\(|_at_minimum\(")


def reduces(source: str) -> bool:
    return REDUCTION.search(source) is not None


def test_adr_controllo_dell_esposizione_the_domain_sums_each_side_with_a_flow_excluded_on_request() -> None:
    summed = inspect.getsource(account_exposure)
    reading = inspect.getsource(account_exposure_reading)

    assert "position.side is side" in summed
    assert "excluding=flow.id" in reading
    assert "holds_account" in reading


def test_adr_controllo_dell_esposizione_the_account_comes_after_the_flow_and_blocks_without_reducing() -> None:
    opening = inspect.getsource(RiskCheck._opening)
    within = inspect.getsource(RiskCheck._within_account)

    assert "account_exposure_limit" in inspect.getsource(RiskState)
    assert "self._committed(self._within_account(self._open(" in opening
    assert "BlockedDecision(outcome.asset, limit.opening_reason(" in within
    assert not reduces(within)
    assert ".adding(" in inspect.getsource(RiskCheck._committed)


def test_adr_controllo_dell_esposizione_no_computation_without_limit_or_option() -> None:
    reading = inspect.getsource(ReadCycleFlowUseCase._exposure_of)

    assert reading.index("return AccountExposureReading()") < reading.index("AccountExposureReading.of(")


def test_adr_controllo_dell_esposizione_a_reduction_to_the_limit_of_the_account_is_found() -> None:
    assert reduces("return sizing.adjusted(limit.amount - exposure, sizing.leverage, adjustment)")
