from enum import StrEnum


class ExchangeNetwork(StrEnum):
    """The network an exchange trades on: the one its adapter is configured on, never deduced (R0.2.1, Bug 277)."""

    TEST = "test"
    REAL = "real"

    @classmethod
    def of(cls, *, real: bool) -> ExchangeNetwork:
        return cls.REAL if real else cls.TEST

    @property
    def is_test(self) -> bool:
        return self is ExchangeNetwork.TEST
