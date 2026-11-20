from autotrading.domain.sources.volumes import VOLUMES


def test_the_volumes_are_a_per_asset_source_without_parameters_of_its_own() -> None:
    assert (VOLUMES.name, VOLUMES.per_asset, VOLUMES.parameters) == ("volumi", True, ())
    assert VOLUMES.description
    assert VOLUMES.silence_note({}) is None
