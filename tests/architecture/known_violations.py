"""Violations of the architecture rules that are known, each with the Bug that removes it.

This list may only shrink: a new violation is a red test, and an entry the code no longer violates is a red test
until it is removed. An entry never exists without its Bug on the board.
"""

from tests.support.architecture import Rule

BUG_CYCLE_RULES_IN_BOOTSTRAP = 170
BUG_STRICTER_RULES = 177

KNOWN_VIOLATIONS: dict[Rule, dict[str, int]] = {
    Rule.PORTS_IN_PORTS_MODULES: {},
    Rule.PORT_NAMES: {},
    Rule.BOOTSTRAP_WITHOUT_DECISIONS: {
        "bootstrap.py:CycleJournalFromContexts.call_cost": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:CycleJournalFromContexts.describe": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:OrdersFromOrders.execute": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:_authentication": BUG_STRICTER_RULES,
        "bootstrap.py:_credentials_private_key": BUG_STRICTER_RULES,
        "bootstrap.py:_credentials_public_key": BUG_STRICTER_RULES,
        "bootstrap.py:_environment": BUG_STRICTER_RULES,
        "bootstrap.py:_optional_secret": BUG_STRICTER_RULES,
        "bootstrap.py:_required": BUG_STRICTER_RULES,
        "bootstrap.py:_secret": BUG_STRICTER_RULES,
        "bootstrap.py:slippage_from": BUG_STRICTER_RULES,
    },
    Rule.BOOTSTRAP_WITHOUT_CONSTANTS: {
        "bootstrap.py:DEFAULT_CREDENTIALS_KEY_VERSION": BUG_STRICTER_RULES,
        "bootstrap.py:DEFAULT_DATABASE_PORT": BUG_STRICTER_RULES,
        "bootstrap.py:HYPERLIQUID": BUG_STRICTER_RULES,
        "bootstrap.py:MODEL_CATALOG": BUG_STRICTER_RULES,
        "bootstrap.py:PROVIDER_TIMEOUT_SECONDS": BUG_STRICTER_RULES,
        "bootstrap.py:SLIPPAGE_SETTING": BUG_STRICTER_RULES,
        "bootstrap.py:SOURCE_CATALOG": BUG_STRICTER_RULES,
        "bootstrap.py:SUPPORTED_ENVIRONMENTS": BUG_STRICTER_RULES,
        "bootstrap.py:TELEGRAM_BOT_SETTING": BUG_STRICTER_RULES,
        "bootstrap.py:operations": BUG_STRICTER_RULES,
    },
    Rule.BOOTSTRAP_WITHOUT_CLASSES: {
        "bootstrap.py:CycleJournalFromContexts": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:OrdersFromOrders": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:AgentFromAgent": BUG_STRICTER_RULES,
        "bootstrap.py:ApiExchanges": BUG_STRICTER_RULES,
        "bootstrap.py:ContextFromAgent": BUG_STRICTER_RULES,
        "bootstrap.py:CycleContext": BUG_STRICTER_RULES,
        "bootstrap.py:CycleDecisions": BUG_STRICTER_RULES,
        "bootstrap.py:CycleOrder": BUG_STRICTER_RULES,
        "bootstrap.py:CycleServices": BUG_STRICTER_RULES,
        "bootstrap.py:FlowPositionsFromOrders": BUG_STRICTER_RULES,
        "bootstrap.py:FlowSummariesFromFlows": BUG_STRICTER_RULES,
        "bootstrap.py:InvalidConfigurationError": BUG_STRICTER_RULES,
        "bootstrap.py:MissingConfigurationError": BUG_STRICTER_RULES,
        "bootstrap.py:OrderExecutionFromOrders": BUG_STRICTER_RULES,
        "bootstrap.py:PublicCredentialsKey": BUG_STRICTER_RULES,
        "bootstrap.py:RiskFromFlows": BUG_STRICTER_RULES,
        "bootstrap.py:SourcesFromSources": BUG_STRICTER_RULES,
        "bootstrap.py:SystemClock": BUG_STRICTER_RULES,
        "bootstrap.py:TenantCyclePorts": BUG_STRICTER_RULES,
        "bootstrap.py:UnconfiguredMessenger": BUG_STRICTER_RULES,
        "bootstrap.py:UndeclaredEnvironmentError": BUG_STRICTER_RULES,
        "bootstrap.py:UnsupportedEnvironmentError": BUG_STRICTER_RULES,
        "bootstrap.py:WorkerConnection": BUG_STRICTER_RULES,
        "bootstrap.py:WorkerExchanges": BUG_STRICTER_RULES,
        "bootstrap.py:WorkerSettings": BUG_STRICTER_RULES,
    },
    Rule.NO_BRIDGES: {
        "bootstrap.py:CycleJournalFromContexts": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:OrdersFromOrders": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:AgentFromAgent": BUG_STRICTER_RULES,
        "bootstrap.py:ContextFromAgent": BUG_STRICTER_RULES,
        "bootstrap.py:FlowPositionsFromOrders": BUG_STRICTER_RULES,
        "bootstrap.py:FlowSummariesFromFlows": BUG_STRICTER_RULES,
        "bootstrap.py:OrderExecutionFromOrders": BUG_STRICTER_RULES,
        "bootstrap.py:RiskFromFlows": BUG_STRICTER_RULES,
        "bootstrap.py:SourcesFromSources": BUG_STRICTER_RULES,
    },
    Rule.LIBRARIES_IN_THEIR_FOLDER: {
        "bootstrap.py:fastapi": BUG_STRICTER_RULES,
        "bootstrap.py:httpx": BUG_STRICTER_RULES,
        "bootstrap.py:sqlalchemy": BUG_STRICTER_RULES,
    },
    Rule.ADAPTERS_DO_NOT_ORCHESTRATE: {},
    Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY: {
        "bootstrap.py:os": BUG_STRICTER_RULES,
    },
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
}
