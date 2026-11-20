from autotrading.domain.sources.social import POSTS, SOCIAL


def test_the_social_source_is_a_per_asset_source_whose_adapters_declare_the_number_of_posts() -> None:
    assert (SOCIAL.name, SOCIAL.per_asset, SOCIAL.parameters) == ("social", True, ())
    assert SOCIAL.description
    assert SOCIAL.silence_note({}) is None
    assert POSTS == "numero_messaggi"
