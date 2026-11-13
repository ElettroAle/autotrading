"""What a step of a cycle produced, kept in its record as JSON data (R1.7.1)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from autotrading.adapters.outbound.json.json_document import json_document

AT = datetime(2026, 11, 13, 9, 30, tzinfo=UTC)
FLOW_ID = UUID("00000000-0000-0000-0000-000000000001")


class Side(Enum):
    LONG = "long"


@dataclass(frozen=True)
class Opening:
    asset: str
    value: Decimal
    side: Side


def test_scalars_keep_their_value() -> None:
    assert json_document(None) is None
    assert json_document(True) is True
    assert json_document(3) == 3
    assert json_document("BTC") == "BTC"


def test_amounts_identifiers_and_moments_become_text() -> None:
    assert json_document(Decimal("0.10")) == "0.10"
    assert json_document(FLOW_ID) == str(FLOW_ID)
    assert json_document(AT) == "2026-11-13T09:30:00+00:00"


def test_an_enumeration_keeps_its_value() -> None:
    assert json_document(Side.LONG) == "long"


def test_mappings_and_collections_are_walked() -> None:
    assert json_document({1: Decimal("2")}) == {"1": "2"}
    assert json_document((Decimal("1"), [Side.LONG])) == ["1", ["long"]]
    assert json_document(frozenset({"BTC"})) == ["BTC"]


def test_a_dataclass_carries_its_type_and_fields() -> None:
    assert json_document(Opening("BTC", Decimal("12.5"), Side.LONG)) == {
        "tipo": "Opening",
        "asset": "BTC",
        "value": "12.5",
        "side": "long",
    }


def test_a_dataclass_type_and_any_other_value_become_text() -> None:
    assert json_document(Opening) == str(Opening)
    assert json_document(object.__new__(type("Opaque", (), {"__str__": lambda _: "opaque"}))) == "opaque"
