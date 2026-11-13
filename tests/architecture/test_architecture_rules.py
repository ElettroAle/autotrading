from dataclasses import dataclass
from textwrap import dedent

import pytest

from tests.support.architecture import Rule, SourceModule, violations_of


@dataclass(frozen=True, slots=True)
class Case:
    rule: Rule
    path: str
    source: str

    @property
    def module(self) -> SourceModule:
        return SourceModule.parse(self.path, dedent(self.source))

    def __str__(self) -> str:
        return f"{self.rule}:{self.path}"


VIOLATING = [
    Case(Rule.PORTS_IN_PORTS_MODULES, "bootstrap.py", "from typing import Protocol\nclass Reader(Protocol): ...\n"),
    Case(Rule.PORTS_IN_PORTS_MODULES, "domain/flows/flow.py", "import typing\nclass Rule(typing.Protocol): ...\n"),
    Case(Rule.PORTS_IN_PORTS_MODULES, "adapters/outbound/httpx/news.py", "class NewsPort: ...\n"),
    Case(Rule.PORTS_IN_PORTS_MODULES, "application/flows/create_flow.py", "class Clock(Protocol[T]): ...\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "def wire(x):\n    if x:\n        return 1\n    return 2\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "def wire(x):\n    return x * 2\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "def wire(x):\n    return [y for y in x if y]\n"),
    Case(
        Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "class Bridge:\n    def go(self, x):\n        return x or 0\n"
    ),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "def wire(x):\n    for y in x:\n        y()\n"),
    Case(
        Rule.BOOTSTRAP_WITHOUT_DECISIONS,
        "bootstrap.py",
        "def wire(x):\n    try:\n        x()\n    finally:\n        x()\n",
    ),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "wire = lambda x: 1 if x else 2\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_BUSINESS_CONSTANTS, "bootstrap.py", 'USDC = "USDC"\n'),
    Case(Rule.BOOTSTRAP_WITHOUT_BUSINESS_CONSTANTS, "bootstrap.py", "WHOLE_UNIT: Decimal = Decimal(1)\n"),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "application/cycles/run.py", "import threading\n"),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "domain/flows/flow.py", "from os import environ\n"),
    Case(
        Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY,
        "application/cycles/run.py",
        "from concurrent.futures import ThreadPoolExecutor\n",
    ),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "domain/orders/order.py", 'CURRENCY = "USDC"\n'),
    Case(
        Rule.CORE_WITHOUT_TECHNOLOGY_NAMES,
        "application/notifications/x.py",
        'def f(c):\n    return f"https://t.me/{c}"\n',
    ),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "domain/accounts/x.py", 'class A:\n    name = "Hyperliquid"\n'),
    Case(Rule.ONLY_PROJECT_EXCEPTIONS_RAISED, "domain/flows/flow.py", 'def f():\n    raise ValueError("no")\n'),
    Case(Rule.ONLY_PROJECT_EXCEPTIONS_RAISED, "adapters/outbound/httpx/news.py", "def f():\n    raise RuntimeError\n"),
    Case(Rule.NO_GENERIC_EXCEPT, "adapters/outbound/httpx/news.py", "try:\n    f()\nexcept Exception:\n    pass\n"),
    Case(Rule.NO_GENERIC_EXCEPT, "bootstrap.py", "try:\n    f()\nexcept:\n    pass\n"),
    Case(Rule.NO_GENERIC_EXCEPT, "domain/x.py", "try:\n    f()\nexcept (KeyError, BaseException):\n    pass\n"),
    Case(
        Rule.USE_CASE_SHAPE,
        "application/flows/create_flow.py",
        "class CreateFlowUseCase:\n    def execute(self): ...\n    def also(self): ...\n",
    ),
    Case(
        Rule.USE_CASE_SHAPE,
        "application/flows/create_flow.py",
        "class AUseCase:\n    def execute(self): ...\nclass BUseCase:\n    def execute(self): ...\n",
    ),
    Case(Rule.COMMAND_SHAPE, "application/flows/create_flow.py", "@dataclass\nclass CreateFlowCommand: ...\n"),
    Case(Rule.COMMAND_SHAPE, "domain/flows/x.py", "class FlowCommand(StrEnum): ...\n"),
    Case(Rule.ADAPTER_NAMES, "adapters/outbound/hyperliquid/user_state.py", "class UserState: ...\n"),
]

CLEAN = [
    Case(Rule.PORTS_IN_PORTS_MODULES, "application/flows/ports.py", "class ClockPort(Protocol): ...\n"),
    Case(
        Rule.BOOTSTRAP_WITHOUT_DECISIONS,
        "bootstrap.py",
        'def wire(x: int | None) -> str | None:\n    return "a" + x.name\n',
    ),
    Case(
        Rule.BOOTSTRAP_WITHOUT_DECISIONS,
        "bootstrap.py",
        "def _required(c, n):\n    if not c.get(n):\n        raise MissingConfigurationError(n)\n",
    ),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "def wire(x):\n    return [y for y in x]\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "adapters/outbound/httpx/news.py", "def f(x):\n    return x or 1\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_BUSINESS_CONSTANTS, "bootstrap.py", 'SLIPPAGE_SETTING = "ORDER_MAX_SLIPPAGE"\n'),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "adapters/outbound/threads/x.py", "import threading\n"),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "domain/flows/flow.py", "from datetime import UTC\n"),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "domain/orders/order.py", '"""Orders as Hyperliquid fills them."""\n'),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "adapters/outbound/hyperliquid/x.py", 'COIN = "USDC"\n'),
    Case(Rule.ONLY_PROJECT_EXCEPTIONS_RAISED, "domain/flows/flow.py", "def f():\n    raise FlowNotFoundError\n"),
    Case(
        Rule.NO_GENERIC_EXCEPT, "adapters/outbound/httpx/news.py", "try:\n    f()\nexcept httpx.HTTPError:\n    pass\n"
    ),
    Case(
        Rule.USE_CASE_SHAPE,
        "application/flows/create_flow.py",
        "class CreateFlowUseCase:\n    def execute(self): ...\n",
    ),
    Case(
        Rule.COMMAND_SHAPE,
        "application/flows/create_flow.py",
        "@dataclass(frozen=True, slots=True)\nclass CreateFlowCommand: ...\n",
    ),
    Case(
        Rule.ADAPTER_NAMES,
        "adapters/outbound/hyperliquid/x.py",
        "class HyperliquidExchangeAdapter: ...\nclass ShapeError(Exception): ...\nclass _State: ...\n",
    ),
]


@pytest.mark.parametrize("case", VIOLATING, ids=str)
def test_rule_catches_the_violation(case: Case) -> None:
    caught = [violation for violation in violations_of(case.module) if violation.rule is case.rule]

    assert caught


@pytest.mark.parametrize("case", CLEAN, ids=str)
def test_rule_leaves_compliant_code_alone(case: Case) -> None:
    caught = [violation for violation in violations_of(case.module) if violation.rule is case.rule]

    assert not caught


def test_violation_names_file_line_rule_and_where_the_code_goes() -> None:
    module = SourceModule.parse("bootstrap.py", "def wire(x):\n    return x or 0\n")

    description = violations_of(module)[0].describe()

    assert description.startswith("src/autotrading/bootstrap.py:2 [bootstrap-senza-decisioni] BoolOp in wire -> ")
    assert "domain o in un caso d'uso" in description


def test_every_rule_has_a_violating_example() -> None:
    assert {case.rule for case in VIOLATING} == set(Rule)
