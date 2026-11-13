from autotrading.application.accounts.errors import CredentialsNotOpenedError
from autotrading.application.flows.errors import FlowCredentialsNotOpenedError
from autotrading.application.orders.errors import OrderCredentialsNotOpenedError
from autotrading.application.verification.errors import VerificationCredentialsNotOpenedError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.verification.verification_access import SealedVerificationAccess, VerificationAccess
from tests.fakes.credential_sealer import SealedVault


class FakeCredentialOpenerAdapter:
    """Opens what the fake sealer sealed, refusing a sealed text that names another tenant or account."""

    def __init__(self, vault: SealedVault) -> None:
        self._vault = vault
        self.opened: list[Account] = []
        self.opened_accesses: list[SealedAccess] = []
        self.opened_addresses: list[SealedAddress] = []

    def open(self, account: Account) -> Credentials:
        self.opened.append(account)
        sealed = self._vault.get(account.credentials.ciphertext)
        if sealed is None:
            raise CredentialsNotOpenedError
        tenant_id, account_id, credentials = sealed
        if (tenant_id, account_id) != (account.tenant_id, account.id):
            raise CredentialsNotOpenedError
        return credentials

    def open_access(self, sealed: SealedAccess) -> TradingAccess:
        opened = self._vault.get(sealed.ciphertext)
        if opened is None:
            raise OrderCredentialsNotOpenedError
        tenant_id, account_id, credentials = opened
        if (tenant_id, account_id) != (sealed.tenant_id, AccountId(sealed.account_id)):
            raise OrderCredentialsNotOpenedError
        self.opened_accesses.append(sealed)
        return TradingAccess(sealed.exchange, credentials.account_address, credentials.secret_key)

    def open_address(self, sealed: SealedAddress) -> str:
        opened = self._vault.get(sealed.ciphertext)
        if opened is None:
            raise FlowCredentialsNotOpenedError
        tenant_id, account_id, credentials = opened
        if (tenant_id, account_id) != (sealed.tenant_id, AccountId(sealed.account_id)):
            raise FlowCredentialsNotOpenedError
        self.opened_addresses.append(sealed)
        return credentials.account_address

    def open_verification(self, sealed: SealedVerificationAccess) -> VerificationAccess:
        opened = self._vault.get(sealed.ciphertext)
        if opened is None:
            raise VerificationCredentialsNotOpenedError
        tenant_id, account_id, credentials = opened
        if (tenant_id, account_id) != (sealed.tenant_id, AccountId(sealed.account_id)):
            raise VerificationCredentialsNotOpenedError
        return VerificationAccess(credentials.account_address, credentials.secret_key)
