from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SealedProviderKey:
    """A provider key encrypted with the public key of the installation, with the version of that key (ADR 0029)."""

    key_version: int
    ciphertext: bytes = field(repr=False)
