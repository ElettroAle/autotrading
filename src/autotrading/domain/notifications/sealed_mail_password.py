from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SealedMailPassword:
    """The password of the mail server of a tenant, sealed with the public key of the installation, with the version
    of that key (ADR server-di-posta-per-tenant): only the worker opens it.
    """

    key_version: int
    ciphertext: bytes = field(repr=False)
