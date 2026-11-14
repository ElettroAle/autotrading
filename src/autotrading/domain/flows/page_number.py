from dataclasses import dataclass

from autotrading.domain.flows.errors import InvalidPageNumberError


@dataclass(frozen=True, slots=True)
class PageNumber:
    """A page of a history of a flow, from the most recent; the first page is 1 (R1.7.3, R2.2.5)."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise InvalidPageNumberError

    def offset(self, per_page: int) -> int:
        return (self.value - 1) * per_page
