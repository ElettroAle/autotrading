from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SealedSourceSecrets:
    """The secret values of the credentials of an adapter of a source, encrypted with the public key of the
    installation, with the version of that key (R4.1.2, ADR credenziali-degli-adapter-delle-fonti).
    """

    key_version: int
    ciphertext: bytes = field(repr=False)
