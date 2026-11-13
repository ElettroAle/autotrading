from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


def json_document(value: object) -> object:
    """The value as JSON data: the record of a cycle keeps what each step produced as it was (R1.7.1)."""
    if value is None or isinstance(value, (bool, int, str, Decimal, UUID, datetime, Enum)):
        return _scalar_of(value)
    if isinstance(value, Mapping):
        return {str(key): json_document(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, frozenset, set)):
        return [json_document(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        document: dict[str, object] = {"tipo": type(value).__name__}
        document.update({each.name: json_document(getattr(value, each.name)) for each in fields(value)})
        return document
    return str(value)


def _scalar_of(value: object) -> object:
    if isinstance(value, Enum):
        return json_document(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return value
