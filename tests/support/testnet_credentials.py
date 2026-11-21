"""The credentials of the testnet account the tests that send orders use (ADR nessun-test-escluso-o-saltato).

HYPERLIQUID_TESTNET_CREDENTIALS_FILE names a JSON file, mounted read only, with "account_address" and "secret_key" of
an API wallet approved for that account. Without it the test fails: it is never skipped.
"""

import json
import os
from pathlib import Path

import pytest

CREDENTIALS_FILE_VARIABLE = "HYPERLIQUID_TESTNET_CREDENTIALS_FILE"


def read_testnet_credentials() -> dict[str, str]:
    location = os.environ.get(CREDENTIALS_FILE_VARIABLE)
    if not location:
        pytest.fail(f"{CREDENTIALS_FILE_VARIABLE} non indica il file delle credenziali della testnet")
    document: dict[str, str] = json.loads(Path(location).read_text(encoding="utf-8"))
    return document
