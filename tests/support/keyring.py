"""The credentials a scenario names by label ("K1", "K2"), all for the same exchange account unless said otherwise."""

from secrets import token_hex

from autotrading.domain.accounts.credentials import Credentials
from tests.support.platform import new_credentials


class Keyring:
    def __init__(self) -> None:
        self._by_label: dict[str, Credentials] = {}
        self._address = f"0x{token_hex(20)}"

    def __getitem__(self, label: str) -> Credentials:
        if label not in self._by_label:
            self._by_label[label] = Credentials(self._address, f"0x{token_hex(32)}")
        return self._by_label[label]

    @staticmethod
    def of_another_exchange_account() -> Credentials:
        return new_credentials()
