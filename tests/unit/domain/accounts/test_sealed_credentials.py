from autotrading.domain.accounts.sealed_credentials import SealedCredentials


def test_representation_shows_the_key_version_but_not_the_ciphertext() -> None:
    sealed = SealedCredentials(key_version=3, ciphertext=b"secret-bytes")

    assert repr(sealed) == "SealedCredentials(key_version=3)"
