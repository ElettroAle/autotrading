from autotrading.application.flows.ports import ReferenceOpenerPort
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.sealed_address import SealedAddress


def reference_of(opener: ReferenceOpenerPort, sealed: SealedAddress, names: frozenset[str]) -> AccountReference:
    """The fields a reader asks, opened; an account of an exchange without credentials has nothing to open and is
    referred to by its identifier (R6.3.2).
    """
    if not sealed.has_credentials:
        return AccountReference.without_credentials(sealed.account_id)
    return opener.open_reference(sealed, names)
