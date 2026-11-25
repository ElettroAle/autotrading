"""The result of a tool: the view it reads, or the error of the project as the API answers it (ADR 0027)."""

import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from http import HTTPStatus

from mcp.types import CallToolResult, TextContent

from autotrading.adapters.inbound.mcp.formats import instant_text
from autotrading.domain.errors import AutotradingError

PROBLEM_TYPE = "about:blank"


def answer_of(read: Callable[[], object]) -> CallToolResult:
    """The view the tool reads, structured and as text; an error of the project is an error result, any other error
    stays the generic failure of the server, which keeps its text to itself.
    """
    try:
        view = read()
    except AutotradingError as error:
        return problem_of(error)
    structured = asdict(view, dict_factory=_plain)  # type: ignore[call-overload]  # every view is a dataclass instance
    return CallToolResult(content=[_text_of(structured)], structured_content=structured)


def problem_of(error: AutotradingError) -> CallToolResult:
    """The reason, the status the error declares and its details: the body of the Problem Details of the API."""
    problem = {
        "type": PROBLEM_TYPE,
        "title": HTTPStatus(error.status_code).phrase,
        "status": error.status_code,
        "detail": str(error),
        **error.details,
    }
    return CallToolResult(content=[_text_of(problem)], is_error=True)


def _plain(fields: list[tuple[str, object]]) -> dict[str, object]:
    """A type of the domain in a view reads as the API writes it: amounts as strings (ADR 0018), instants in ISO 8601
    with the Z, enumerations as their values, sequences as lists."""
    return {name: _plain_value(value) for name, value in fields}


def _plain_value(value: object) -> object:
    if isinstance(value, tuple | list):
        return [_plain_value(item) for item in value]
    if isinstance(value, datetime):
        return instant_text(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    return value


def _text_of(body: dict[str, object]) -> TextContent:
    return TextContent(type="text", text=json.dumps(body, ensure_ascii=False, default=str))
