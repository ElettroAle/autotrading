from autotrading.application.accounts.errors import CredentialsNotOpenedError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from tests.fakes.credential_sealer import SealedVault


class FakeCredentialOpenerAdapter:
    """Opens what the fake sealer sealed, refusing a sealed text that names another tenant or account."""

    def __init__(self, vault: SealedVault) -> None:
        self._vault = vault
        self.opened: list[Account] = []

    def open(self, account: Account) -> Credentials:
        self.opened.append(account)
        sealed = self._vault.get(account.credentials.ciphertext)
        if sealed is None:
            raise CredentialsNotOpenedError
        tenant_id, account_id, credentials = sealed
        if (tenant_id, account_id) != (account.tenant_id, account.id):
            raise CredentialsNotOpenedError
        return credentials
