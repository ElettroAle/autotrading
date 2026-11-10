from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine

from tests.support.postgres import migrated_database


@pytest.fixture(scope="module")
def database(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Engine]:
    with migrated_database(Path(tmp_path_factory.mktemp("database"))) as engine:
        yield engine
