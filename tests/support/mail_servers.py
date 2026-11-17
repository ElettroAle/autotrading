"""The mail servers of the tenants of a test, as the API saves them and the worker opens them (R3.5.5)."""

from autotrading.application.notifications.ports import MailServerAccess
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.mail_server import MailServer, MailServerAddress
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.mail_password_opener import FakeMailPasswordOpenerAdapter
from tests.fakes.mail_password_sealer import FakeMailPasswordSealerAdapter, MailPasswordVault
from tests.fakes.mail_server_repository import InMemoryMailServerRepositoryAdapter, MailServerStore

HOST = "smtp.example.com"
PORT = 587
PASSWORD = "password-per-le-app"  # noqa: S105 - the password of a fake mail server


class MailServers:
    def __init__(self) -> None:
        self.store: MailServerStore = {}
        self.vault: MailPasswordVault = {}

    def repository(self, tenant_id: TenantId) -> InMemoryMailServerRepositoryAdapter:
        return InMemoryMailServerRepositoryAdapter(self.store, tenant_id)

    def sealer(self, tenant_id: TenantId) -> FakeMailPasswordSealerAdapter:
        return FakeMailPasswordSealerAdapter(tenant_id, self.vault)

    def opener(self, tenant_id: TenantId) -> FakeMailPasswordOpenerAdapter:
        return FakeMailPasswordOpenerAdapter(tenant_id, self.vault)

    def access_of(self, tenant_id: TenantId) -> MailServerAccess:
        """What the worker composes to send from the mail server of the tenant of a message."""
        return MailServerAccess(self.repository(tenant_id), self.opener(tenant_id))

    def configure(self, tenant_id: TenantId, username: str, host: str = HOST) -> MailServer:
        """The tenant saved a server, with its user as the sender."""
        address = MailServerAddress(host, PORT, MailSecurity.STARTTLS, username, "")
        server = MailServer.of(tenant_id, address, self.sealer(tenant_id).seal(PASSWORD))
        self.store[tenant_id] = server
        return server
