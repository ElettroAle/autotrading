from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.worker.composition import worker_adapters


def _worker(tmp_path: Path, **overrides: str) -> ConfigurationSource:
    token = tmp_path / "worker_token"
    token.write_text("t0k\n", encoding="utf-8")
    return ConfigurationSource({"WORKER_URL": "http://worker:8000", "WORKER_TOKEN_FILE": str(token)} | overrides)


def test_the_worker_is_reached_at_its_address_with_the_token_of_the_machine(tmp_path: Path) -> None:
    client, token = worker_adapters(_worker(tmp_path))

    assert (str(client.base_url), token) == ("http://worker:8000", "t0k")


@pytest.mark.parametrize("name", ["WORKER_URL", "WORKER_TOKEN_FILE"])
def test_the_worker_must_be_declared(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        worker_adapters(_worker(tmp_path, **{name: ""}))

    assert raised.value.name == name
