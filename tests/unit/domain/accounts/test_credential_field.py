from autotrading.domain.accounts.credential_field import CredentialField


def test_a_field_says_its_name_its_label_and_whether_it_is_secret() -> None:
    field = CredentialField("secret_key", "Chiave dell'API wallet", secret=True)

    assert (field.name, field.label, field.secret) == ("secret_key", "Chiave dell'API wallet", True)
