import json
from collections.abc import Mapping
from dataclasses import dataclass

import pytest
from mcp.types import TextContent

from autotrading.adapters.inbound.mcp.tool_results import answer_of, problem_of
from autotrading.domain.errors import AutotradingError


@dataclass(frozen=True)
class Reading:
    name: str
    values: list[str]


class FlowGoneError(AutotradingError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("flusso non trovato")


class CapitalError(AutotradingError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("capitale oltre il disponibile")

    @property
    def details(self) -> Mapping[str, object]:
        return {"field": "allocated_capital"}


class UnexpectedFailureError(Exception):
    pass


def text_of(content: object) -> dict[str, object]:
    assert isinstance(content, TextContent)
    loaded: dict[str, object] = json.loads(content.text)
    return loaded


def test_a_reading_is_the_structured_view_and_its_text() -> None:
    result = answer_of(lambda: Reading("alfa", ["1.5"]))

    assert not result.is_error
    assert result.structured_content == {"name": "alfa", "values": ["1.5"]}
    assert [text_of(content) for content in result.content] == [{"name": "alfa", "values": ["1.5"]}]


def test_an_error_of_the_project_is_the_problem_the_api_answers() -> None:
    def refused() -> Reading:
        raise CapitalError

    result = answer_of(refused)

    assert result.is_error
    assert result.structured_content is None
    assert [text_of(content) for content in result.content] == [
        {
            "type": "about:blank",
            "title": "Unprocessable Content",
            "status": 422,
            "detail": "capitale oltre il disponibile",
            "field": "allocated_capital",
        }
    ]


def test_an_error_without_details_keeps_its_status_and_reason() -> None:
    (content,) = problem_of(FlowGoneError()).content

    assert text_of(content) == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "flusso non trovato",
    }


def test_any_other_error_is_left_to_the_server() -> None:
    def broken() -> Reading:
        raise UnexpectedFailureError

    with pytest.raises(UnexpectedFailureError):
        answer_of(broken)
