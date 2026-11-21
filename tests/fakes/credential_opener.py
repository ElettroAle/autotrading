from autotrading.application.accounts.errors import CredentialsNotOpenedError
from autotrading.application.flows.errors import FlowCredentialsFieldMissingError, FlowCredentialsNotOpenedError
from autotrading.application.orders.errors import OrderCredentialsNotOpenedError
from autotrading.application.verification.errors import VerificationCredentialsNotOpenedError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.verification.verification_access import SealedVerificationAccess, VerificationAccess
from tests.fakes.credential_sealer import SealedVault
from tests.support.openings import OpeningRegister


class FakeCredentialOpenerAdapter:
    """Opens what the fake sealer sealed, refusing a sealed text that names another tenant or account; every opening,
    opened or refused, goes in the register as the opener of the worker writes it (Bug 179).
    """

    def __init__(self, vault: SealedVault, register: OpeningRegister | None = None) -> None:
        self._vault = vault
        self.register = OpeningRegister() if register is None else register
        self.opened: list[Account] = []
        self.opened_accesses: list[SealedAccess] = []
        self.opened_addresses: list[SealedAddress] = []

    def open(self, account: Account) -> Credentials:
        self.opened.append(account)
        sealed = account.credentials
        credentials = self._opened("conto", sealed.key_version, sealed.ciphertext, account.tenant_id, account.id)
        if credentials is None:
            raise CredentialsNotOpenedError
        return credentials

    def open_access(self, sealed: SealedAccess) -> TradingAccess:
        account_id = AccountId(sealed.account_id)
        credentials = self._opened("ordini", sealed.key_version, sealed.ciphertext, sealed.tenant_id, account_id)
        if credentials is None:
            raise OrderCredentialsNotOpenedError
        self.opened_accesses.append(sealed)
        return TradingAccess(sealed.exchange, credentials.values)

    def open_reference(self, sealed: SealedAddress, names: frozenset[str]) -> AccountReference:
        account_id = AccountId(sealed.account_id)
        credentials = self._opened("flussi", sealed.key_version, sealed.ciphertext, sealed.tenant_id, account_id)
        if credentials is None:
            raise FlowCredentialsNotOpenedError
        self.opened_addresses.append(sealed)
        if not names <= credentials.values.keys():
            raise FlowCredentialsFieldMissingError
        return AccountReference({name: credentials.values[name] for name in names})

    def open_cycle_access(self, sealed: SealedAddress) -> CycleAccess:
        account_id = AccountId(sealed.account_id)
        credentials = self._opened("ciclo", sealed.key_version, sealed.ciphertext, sealed.tenant_id, account_id)
        if credentials is None:
            raise FlowCredentialsNotOpenedError
        return CycleAccess(credentials.values)

    def open_verification(self, sealed: SealedVerificationAccess) -> VerificationAccess:
        account_id = AccountId(sealed.account_id)
        credentials = self._opened("verifica", sealed.key_version, sealed.ciphertext, sealed.tenant_id, account_id)
        if credentials is None:
            raise VerificationCredentialsNotOpenedError
        return VerificationAccess(credentials.values)

    def _opened(
        self, purpose: str, key_version: int, ciphertext: bytes, tenant_id: TenantId, account_id: AccountId
    ) -> Credentials | None:
        credentials = self._credentials_in(ciphertext, tenant_id, account_id)
        subject = f"conto {account_id.value}"
        self.register.record(purpose, subject, tenant_id, key_version, opened=credentials is not None)
        return credentials

    def _credentials_in(self, ciphertext: bytes, tenant_id: TenantId, account_id: AccountId) -> Credentials | None:
        sealed = self._vault.get(ciphertext)
        if sealed is None:
            return None
        owner, account, credentials = sealed
        if (owner, account) != (tenant_id, account_id):
            return None
        return credentials
