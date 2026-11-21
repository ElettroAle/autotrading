"""Violations of the architecture rules that are known, each with the Bug that removes it.

This list may only shrink: a new violation is a red test, and an entry the code no longer violates is a red test
until it is removed. An entry never exists without its Bug on the board.
"""

from tests.support.architecture import Rule

KNOWN_VIOLATIONS: dict[Rule, dict[str, int]] = {
    Rule.PORTS_IN_PORTS_MODULES: {},
    Rule.PORT_NAMES: {},
    Rule.BOOTSTRAP_WITHOUT_DECISIONS: {},
    Rule.BOOTSTRAP_WITHOUT_CONSTANTS: {},
    Rule.BOOTSTRAP_WITHOUT_CLASSES: {},
    Rule.NO_BRIDGES: {},
    Rule.LIBRARIES_IN_THEIR_FOLDER: {},
    Rule.ADAPTERS_DO_NOT_ORCHESTRATE: {},
    Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY: {},
    Rule.CORE_WITHOUT_TECHNOLOGY_NAMES: {},
    Rule.ONLY_PROJECT_EXCEPTIONS_RAISED: {},
    Rule.ERROR_SHAPE: {},
    Rule.NO_GENERIC_EXCEPT: {},
    Rule.USE_CASE_SHAPE: {},
    Rule.COMMAND_SHAPE: {},
    Rule.ADAPTER_NAMES: {},
    Rule.NO_GENERIC_FOLDERS: {},
    Rule.NO_ANY: {},
    Rule.TYPE_IGNORE_EXPLAINED: {},
    Rule.CONFIGURATION_THROUGH_SOURCE: {},
    Rule.SETTINGS_IN_THEIR_FOLDER: {},
    Rule.BOOTSTRAP_CONFIGURES_THROUGH_COMPOSITIONS: {},
    # The tests that send orders on the testnet wait for the secret of its credentials (ADR
    # nessun-test-escluso-o-saltato).
    Rule.NO_EXCLUDED_TESTS: {
        ".github/actions/pytest-run/action.yml:testnet_credentials": 643,
        "tests/integration/hyperliquid/test_exchange_testnet.py:test_approved_credentials_read_the_account_value": 643,
        "tests/integration/hyperliquid/test_exchange_testnet.py:"
        "test_a_wallet_not_approved_for_the_account_is_rejected_by_the_exchange": 643,
        "tests/integration/hyperliquid/test_protections_testnet.py:"
        "test_the_protections_of_the_whole_position_are_placed_read_and_cancelled": 643,
    },
}
