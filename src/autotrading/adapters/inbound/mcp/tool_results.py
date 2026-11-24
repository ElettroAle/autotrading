"""The result of a tool: the view it reads, or the error of the project as the API answers it (ADR 0027)."""

import json
from collections.abc import Callable
from dataclasses import asdict
from http import HTTPStatus

from mcp.types import CallToolResult, TextContent

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
    structured = asdict(view)  # type: ignore[call-overload]  # every view of the tools is a dataclass instance
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


def _text_of(body: dict[str, object]) -> TextContent:
    return TextContent(type="text", text=json.dumps(body, ensure_ascii=False, default=str))
