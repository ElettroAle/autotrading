"""The identity directory as the scenarios see it: people with a stable identifier, a display name and roles."""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Person:
    name: str
    object_id: str = field(default_factory=lambda: str(uuid4()))
    display_name: str = ""
    roles: set[str] = field(default_factory=set)


@dataclass
class Directory:
    people: dict[str, Person] = field(default_factory=dict)

    def person(self, name: str) -> Person:
        return self.people.setdefault(name, Person(name, display_name=name))
