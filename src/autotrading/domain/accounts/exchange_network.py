from enum import StrEnum

TEST_INSTALLATION = "dev"


class ExchangeNetwork(StrEnum):
    """The network of the exchanges an installation trades on (R0.2.1, ADR 0087)."""

    TEST = "test"
    REAL = "real"

    @classmethod
    def of_installation(cls, environment: str) -> ExchangeNetwork:
        """Test networks in dev, real ones in prod: dev never moves real money."""
        return cls.TEST if environment == TEST_INSTALLATION else cls.REAL

    @property
    def is_test(self) -> bool:
        return self is ExchangeNetwork.TEST
