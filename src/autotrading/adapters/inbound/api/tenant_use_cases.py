from dataclasses import dataclass

from autotrading.application.accounts.register_account import RegisterAccountUseCase


@dataclass(frozen=True, slots=True)
class TenantUseCases:
    """The use cases of one request, built by bootstrap.for_tenant on adapters bound to the tenant of the request."""

    register_account: RegisterAccountUseCase
