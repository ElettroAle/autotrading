from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SealedCredentials:
    """Credentials encrypted with the public key of the installation, with the version of that key (ADR 0007)."""

    key_version: int
    ciphertext: bytes = field(repr=False)

    @classmethod
    def none(cls) -> SealedCredentials:
        """What an account of an exchange without credentials keeps: nothing to open (R6.3.2)."""
        return cls(0, b"")

    @property
    def is_empty(self) -> bool:
        return not self.ciphertext
