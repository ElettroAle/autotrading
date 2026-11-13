"""Violations of the architecture rules that are known, each with the Bug that removes it.

This list may only shrink: a new violation is a red test, and an entry the code no longer violates is a red test
until it is removed. An entry never exists without its Bug on the board.
"""

from tests.support.architecture import Rule

BUG_CYCLE_RULES_IN_BOOTSTRAP = 170
BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP = 171
BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON = 173

KNOWN_VIOLATIONS: dict[Rule, dict[str, int]] = {
    Rule.PORTS_IN_PORTS_MODULES: {
        "bootstrap.py:ActivityReaderPort": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:ExecutionsReaderPort": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:ManualClosingRecorder": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:Notifier": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:ScheduledFlowsSource": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
    },
    Rule.BOOTSTRAP_WITHOUT_DECISIONS: {
        "bootstrap.py:AccountActivityFromAccounts.activity": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:AccountExecutionsFromAccounts.since": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:AccountReadingFromAccounts.flow_on": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:AccountReadingFromAccounts.read": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:CycleFlow.positions": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:CycleJournalFromContexts.call_cost": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:CycleJournalFromContexts.describe": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:FlowDirectory._entry": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:FlowPauseFromFlows.pause_affected_by": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:FlowStateFromFlows._snapshot": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:ModelSettingsFromAgent.selection": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:NotifiedCycles.record": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:OrdersFromOrders.execute": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:RiskFromFlows.check": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:SourceSettingsFromSources.selection": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:UnattributableNotices.notice": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:SourcesFromSources.collect": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:TradingAccessFromAccounts.access": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:_agent_data_of": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:_intent_of": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:_scalar_of": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:_summary_of": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:_unattributable_notification": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:flow_of_cycle": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:json_of": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:ClosedPositionsFromOpenings.add_closed_outside": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:FlowPositionsFromOrders.close": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:ManualClosingsRecordedInFlows.close": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:_flow_order_of": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:_follow_closing": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:_follow_order": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:_opening_notification": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:_result_of": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:AccountFlowsFromFlows._operating_on": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:AccountFlowsFromFlows.archive": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:FlowAccountsFromAccounts.account": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:FlowDirectoryFromFlows.exists": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:ProviderKeyUsageFromFlows.flows_using": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:activity_readers_for": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:create_worker_application": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:cycle_services": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:exchanges_for": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:executions_readers_for": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:markets_for": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:order_exchanges_for": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
        "bootstrap.py:record_actual_prices": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
    },
    Rule.BOOTSTRAP_WITHOUT_BUSINESS_CONSTANTS: {
        "bootstrap.py:MODEL_REFUSALS": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:SOURCE_REFUSALS": BUG_CYCLE_RULES_IN_BOOTSTRAP,
        "bootstrap.py:USDC": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
        "bootstrap.py:WHOLE_UNIT": BUG_HISTORY_NOTIFICATIONS_CURRENCY_IN_BOOTSTRAP,
    },
    Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY: {
        "application/cycles/source_collector.py:concurrent.futures": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
    },
    Rule.CORE_WITHOUT_TECHNOLOGY_NAMES: {
        "domain/notifications/link_code.py:<modulo>": BUG_API_RULES_AND_PORTS_OUTSIDE_HEXAGON,
    },
    Rule.ONLY_PROJECT_EXCEPTIONS_RAISED: {},
    Rule.NO_GENERIC_EXCEPT: {},
    Rule.USE_CASE_SHAPE: {},
    Rule.COMMAND_SHAPE: {},
    Rule.ADAPTER_NAMES: {},
}
