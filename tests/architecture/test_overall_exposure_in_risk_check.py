"""ADR-esposizione-complessiva-nel-controllo-del-rischio: the overall exposure limits are a step of the existing risk
check, never a separate check after it. Only the risk check reads the exposure of the open positions and makes the
overall reductions.
"""

import ast

from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

RISK_CHECK = "domain/flows/risk_check.py"
# The exposure of the open positions in the state of the risk, and the kinds of the overall reductions.
OVERALL_EXPOSURE = frozenset({"open_margin", "open_value", "TOTAL_MARGIN", "TOTAL_VALUE"})


def overall_exposure_readers(modules: list[SourceModule]) -> list[str]:
    """The modules that read the exposure of the open positions or make an overall reduction."""
    return sorted(
        {
            module.path
            for module in modules
            for node in ast.walk(module.tree)
            if isinstance(node, ast.Attribute) and node.attr in OVERALL_EXPOSURE
        }
    )


def test_adr_overall_exposure_only_the_risk_check_applies_it() -> None:
    assert overall_exposure_readers(source_modules(SOURCE_ROOT)) == [RISK_CHECK]


def test_adr_overall_exposure_a_separate_check_after_the_risk_check_is_a_violation() -> None:
    separate = SourceModule.parse(
        "application/flows/check_overall_exposure.py",
        "def reduced(state, outcome):\n    return state.open_margin + outcome.margin\n",
    )
    reduction = SourceModule.parse(
        "domain/flows/overall_exposure.py",
        "def kind():\n    return AdjustmentKind.TOTAL_VALUE\n",
    )

    assert overall_exposure_readers([separate, reduction]) == [
        "application/flows/check_overall_exposure.py",
        "domain/flows/overall_exposure.py",
    ]
