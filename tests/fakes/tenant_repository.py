from autotrading.application.tenancy.errors import TenantAlreadyExistsError
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId


class InMemoryTenantRepositoryAdapter:
    def __init__(self) -> None:
        self.tenants: list[Tenant] = []
        self._hidden_until_added: Tenant | None = None
        self._refuse_next_add = False

    def find_by_member(self, user_id: UserId) -> Tenant | None:
        return next((tenant for tenant in self.tenants if tenant.owner == user_id), None)

    def add(self, tenant: Tenant) -> None:
        if self._refuse_next_add:
            self._refuse_next_add = False
            raise TenantAlreadyExistsError(tenant.owner)
        if self._hidden_until_added is not None:
            self.tenants.append(self._hidden_until_added)
            self._hidden_until_added = None
        if self.find_by_member(tenant.owner) is not None:
            raise TenantAlreadyExistsError(tenant.owner)
        self.tenants.append(tenant)

    def create_concurrently_on_next_add(self, tenant: Tenant) -> None:
        """Simulates another request that founds the same user's tenant between the lookup and the insert."""
        self._hidden_until_added = tenant

    def refuse_next_add_without_storing(self) -> None:
        """Simulates a store that reports a conflict but then shows no tenant for the user."""
        self._refuse_next_add = True
