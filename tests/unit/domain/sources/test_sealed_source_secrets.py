from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets


def test_representation_shows_the_key_version_but_not_the_ciphertext() -> None:
    sealed = SealedSourceSecrets(key_version=3, ciphertext=b"secret-bytes")

    assert repr(sealed) == "SealedSourceSecrets(key_version=3)"
