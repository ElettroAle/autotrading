"""ADR-test-testnet-con-ordini-cancellati: the tests that sent orders on the testnet with the credentials of a testnet
wallet are gone, with their marker, their exclusion from the pipeline and their known violations; no test reads the
credentials of a testnet wallet.
"""

import tomllib
from pathlib import Path

from tests.architecture.known_violations import KNOWN_VIOLATIONS
from tests.support.architecture import Rule, pipeline_excluded_markers

REPOSITORY = Path(__file__).resolve().parents[2]
PIPELINE_TEST_RUN = REPOSITORY / ".github" / "actions" / "pytest-run" / "action.yml"
DROPPED_MARKER = "testnet_credentials"
CREDENTIALS_FILE_VARIABLE = "HYPERLIQUID_TESTNET_CREDENTIALS_FILE"


def declared_markers() -> set[str]:
    document = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    return {line.split(":", 1)[0] for line in document["tool"]["pytest"]["ini_options"]["markers"]}


def test_the_pipeline_leaves_out_only_the_pipeline_marker() -> None:
    assert pipeline_excluded_markers(PIPELINE_TEST_RUN.read_text(encoding="utf-8")) == {"pipeline"}


def test_the_marker_of_the_testnet_credentials_is_not_declared() -> None:
    assert DROPPED_MARKER not in declared_markers()


def test_no_excluded_test_is_a_known_violation() -> None:
    assert KNOWN_VIOLATIONS[Rule.NO_EXCLUDED_TESTS] == {}


def test_no_test_reads_the_credentials_of_a_testnet_wallet() -> None:
    readers = [
        path.relative_to(REPOSITORY).as_posix()
        for path in (REPOSITORY / "tests").rglob("*.py")
        if path.resolve() != Path(__file__).resolve() and CREDENTIALS_FILE_VARIABLE in path.read_text(encoding="utf-8")
    ]

    assert readers == []
