from collections.abc import Callable

import pytest

SELECTION_TAGS = frozenset({"wip", "pipeline"})


def pytest_bdd_apply_tag(tag: str, function: Callable[..., object]) -> bool:
    if tag in SELECTION_TAGS:
        getattr(pytest.mark, tag)(function)
    # The requirement tag (e.g. R0.5.1) is traceability for the board, not a pytest marker.
    return True
