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
    },
    Rule.BOOTSTRAP_WITHOUT_CONSTANTS: {
        "bootstrap.py:MODEL_CATALOG": BUG_STRICTER_RULES,
        "bootstrap.py:PROVIDER_TIMEOUT_SECONDS": BUG_STRICTER_RULES,
        "bootstrap.py:SOURCE_CATALOG": BUG_STRICTER_RULES,
        "bootstrap.py:operations": BUG_STRICTER_RULES,
    },
    Rule.BOOTSTRAP_WITHOUT_CLASSES: {
        "bootstrap.py:CycleJournalFromContexts": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:AgentFromAgent": BUG_STRICTER_RULES,
        "bootstrap.py:ApiExchanges": BUG_STRICTER_RULES,
        "bootstrap.py:ContextFromAgent": BUG_STRICTER_RULES,
        "bootstrap.py:CycleContext": BUG_STRICTER_RULES,
        "bootstrap.py:CycleDecisions": BUG_STRICTER_RULES,
        "bootstrap.py:CycleServices": BUG_STRICTER_RULES,
        "bootstrap.py:FlowPositionsFromOrders": BUG_STRICTER_RULES,
        "bootstrap.py:FlowSummariesFromFlows": BUG_STRICTER_RULES,
        "bootstrap.py:OrderExecutionFromOrders": BUG_STRICTER_RULES,
        "bootstrap.py:RiskFromFlows": BUG_STRICTER_RULES,
        "bootstrap.py:SourcesFromSources": BUG_STRICTER_RULES,
        "bootstrap.py:SystemClock": BUG_STRICTER_RULES,
        "bootstrap.py:TenantCyclePorts": BUG_STRICTER_RULES,
        "bootstrap.py:WorkerConnection": BUG_STRICTER_RULES,
        "bootstrap.py:WorkerExchanges": BUG_STRICTER_RULES,
    },
    Rule.NO_BRIDGES: {
        "bootstrap.py:CycleJournalFromContexts": BUG_CYCLE_RULES_IN_BOOTSTRAP,
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
}
