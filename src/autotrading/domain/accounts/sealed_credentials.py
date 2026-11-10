from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SealedCredentials:
    """Credentials encrypted with the public key of the installation, with the version of that key (ADR 0007)."""

    key_version: int
    ciphertext: bytes = field(repr=False)
