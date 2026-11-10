"""Step patterns whose quoted placeholders never cross a quote, so two similar steps cannot match the same text."""

import re

from pytest_bdd import parsers

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def quoted(text: str) -> parsers.StepParser:
    pattern = "".join(
        f'(?P<{piece}>[^"]+)' if index % 2 else re.escape(piece) for index, piece in enumerate(_PLACEHOLDER.split(text))
    )
    return parsers.re(f"^{pattern}$")
