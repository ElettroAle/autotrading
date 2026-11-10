from dataclasses import dataclass, field

from autotrading.domain.accounts.errors import CredentialsRequiredError

MASK = "***"


@dataclass(frozen=True, slots=True)
class Credentials:
    """The keys the user created on the exchange: the account address and the secret that signs for it.

    They never appear in answers, logs, errors or exceptions, so the representation masks them (R0.2.3).
    """

    account_address: str = field(repr=False)
    secret_key: str = field(repr=False)

    def __post_init__(self) -> None:
        address, secret = self.account_address.strip(), self.secret_key.strip()
        if not address or not secret:
            raise CredentialsRequiredError
        object.__setattr__(self, "account_address", address)
        object.__setattr__(self, "secret_key", secret)

    def __repr__(self) -> str:
        return f"Credentials({MASK})"

    __str__ = __repr__
