from dataclasses import dataclass
from textwrap import dedent

import pytest

from tests.support.architecture import (
    SOURCE_PREFIX,
    Rule,
    SourceModule,
    Violation,
    pipeline_excluded_markers,
    violations_of,
    violations_of_file,
)

# The rule on the tests reads files of the whole repository, the other rules the modules of src/autotrading.
REPOSITORY_FOLDERS = ("tests/", "specs/", "dashboard/", ".github/")
PIPELINE_TEST_RUN = ".github/actions/pytest-run/action.yml"
CREDENTIALS_MARKER = frozenset({"testnet_credentials"})


@dataclass(frozen=True, slots=True)
class Case:
    rule: Rule
    path: str
    source: str
    excluded_markers: frozenset[str] = frozenset()

    @property
    def module(self) -> SourceModule:
        return SourceModule.parse(self.path, dedent(self.source))

    @property
    def violations(self) -> list[Violation]:
        if self.path.startswith(REPOSITORY_FOLDERS):
            return violations_of_file(self.path, dedent(self.source), self.excluded_markers)
        return violations_of(self.module)

    def __str__(self) -> str:
        return f"{self.rule}:{self.path}"


ORCHESTRATING_ADAPTER = (
    "class SqlAlchemyAccessAdapter:\n"
    "    def __init__(self, accounts: AccountRepositoryPort, opener: CredentialOpenerPort) -> None: ...\n"
)
CONTRACT_IMPORTS = (
    "from autotrading.application.orders.ports import ExchangePort\n"
    "from autotrading.application.orders.errors import OrderAccountNotFoundError\n"
    "from autotrading.application.errors import ApplicationError\n"
    "class SqlAlchemyAccountsAdapter:\n"
    "    def __init__(self, engine: Engine, tenant: TenantId) -> None: ...\n"
)
DECORATOR = (
    "class HttpxRetryingExchangeAdapter(ExchangePort):\n    def __init__(self, inner: ExchangePort) -> None: ...\n"
)
UNDECLARED_DECORATOR = "class HttpxRetryingAdapter:\n    def __init__(self, inner: ExchangePort) -> None: ...\n"
CONFIGURATION_READER = "def _required(c, n):\n    if not c.get(n):\n        raise MissingConfigurationError(n)\n"
SOURCE_IN_A_CONSTRUCTOR = (
    "class SqlAlchemyDatabaseAdapter:\n    def __init__(self, source: ConfigurationSource) -> None: ...\n"
)
BOOTSTRAP_COMPOSITION = (
    "def create_application(configuration):\n"
    "    source = ConfigurationSource(configuration)\n"
    "    environment = source.environment()\n"
    "    return api_adapters(source, sqlalchemy_adapters(source), environment)\n"
)

VIOLATING = [
    Case(Rule.PORTS_IN_PORTS_MODULES, "bootstrap.py", "from typing import Protocol\nclass Reader(Protocol): ...\n"),
    Case(Rule.PORTS_IN_PORTS_MODULES, "domain/flows/flow.py", "import typing\nclass Rule(typing.Protocol): ...\n"),
    Case(Rule.PORTS_IN_PORTS_MODULES, "adapters/outbound/rss/news.py", "class NewsPort: ...\n"),
    Case(Rule.PORTS_IN_PORTS_MODULES, "application/flows/create_flow.py", "class Clock(Protocol[T]): ...\n"),
    Case(Rule.PORT_NAMES, "application/orders/ports.py", "class Exchange(Protocol): ...\n"),
    Case(Rule.PORT_NAMES, "application/orders/ports.py", "@dataclass(frozen=True)\nclass ExchangePort: ...\n"),
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
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", CONFIGURATION_READER),
    Case(Rule.BOOTSTRAP_WITHOUT_CONSTANTS, "bootstrap.py", 'USDC = "USDC"\n'),
    Case(Rule.BOOTSTRAP_WITHOUT_CONSTANTS, "bootstrap.py", "WHOLE_UNIT: Decimal = Decimal(1)\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_CONSTANTS, "bootstrap.py", 'SLIPPAGE_SETTING = "ORDER_MAX_SLIPPAGE"\n'),
    Case(Rule.BOOTSTRAP_WITHOUT_CLASSES, "bootstrap.py", "class WorkerSettings: ...\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_CLASSES, "bootstrap.py", "class MissingConfigurationError(ApplicationError): ...\n"),
    Case(Rule.NO_BRIDGES, "bootstrap.py", "class TradingAccessFromAccounts: ...\n"),
    Case(Rule.NO_BRIDGES, "adapters/outbound/sqlalchemy/x.py", "class AccountsBridge: ...\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "adapters/inbound/api/authentication.py", "import jwt\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "adapters/outbound/sqlalchemy/x.py", "import httpx\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "bootstrap.py", "from sqlalchemy import Engine\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "domain/flows/flow.py", "import pydantic\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "adapters/outbound/redis/x.py", "import redis\n"),
    Case(
        Rule.ADAPTERS_DO_NOT_ORCHESTRATE,
        "adapters/outbound/sqlalchemy/x.py",
        "from autotrading.application.orders.open_position import OpenPositionUseCase\n",
    ),
    Case(Rule.ADAPTERS_DO_NOT_ORCHESTRATE, "adapters/outbound/sqlalchemy/x.py", ORCHESTRATING_ADAPTER),
    Case(
        Rule.ADAPTERS_DO_NOT_ORCHESTRATE,
        "adapters/outbound/telegram/x.py",
        "class HttpxReaderAdapter:\n    def __init__(self, readers: Mapping[str, ActivityReaderPort]) -> None: ...\n",
    ),
    Case(Rule.ADAPTERS_DO_NOT_ORCHESTRATE, "adapters/outbound/telegram/x.py", UNDECLARED_DECORATOR),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "application/cycles/run.py", "import threading\n"),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "domain/flows/flow.py", "from os import environ\n"),
    Case(
        Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY,
        "application/cycles/run.py",
        "from concurrent.futures import ThreadPoolExecutor\n",
    ),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "bootstrap.py", "import threading\n"),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "domain/orders/order.py", 'CURRENCY = "USDC"\n'),
    Case(
        Rule.CORE_WITHOUT_TECHNOLOGY_NAMES,
        "application/notifications/x.py",
        'def f(c):\n    return f"https://t.me/{c}"\n',
    ),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "domain/accounts/x.py", 'class A:\n    name = "Hyperliquid"\n'),
    Case(Rule.ONLY_PROJECT_EXCEPTIONS_RAISED, "domain/flows/flow.py", 'def f():\n    raise ValueError("no")\n'),
    Case(Rule.ONLY_PROJECT_EXCEPTIONS_RAISED, "adapters/outbound/rss/news.py", "def f():\n    raise RuntimeError\n"),
    Case(Rule.ERROR_SHAPE, "adapters/outbound/hyperliquid/x.py", "class ShapeError(Exception): ...\n"),
    Case(Rule.ERROR_SHAPE, "domain/flows/x.py", "class FlowNotFoundError(DomainProblem): ...\n"),
    Case(Rule.ERROR_SHAPE, "domain/flows/x.py", "class Refusal(ValueError): ...\n"),
    Case(Rule.NO_GENERIC_EXCEPT, "adapters/outbound/rss/news.py", "try:\n    f()\nexcept Exception:\n    pass\n"),
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
    Case(
        Rule.USE_CASE_SHAPE,
        "application/flows/free_capital.py",
        "class ReadFreeCapitalUseCase:\n    def execute(self): ...\n",
    ),
    Case(Rule.COMMAND_SHAPE, "application/flows/create_flow.py", "@dataclass\nclass CreateFlowCommand: ...\n"),
    Case(Rule.COMMAND_SHAPE, "domain/flows/x.py", "class FlowCommand(StrEnum): ...\n"),
    Case(
        Rule.COMMAND_SHAPE,
        "application/sources/ports.py",
        "@dataclass(frozen=True, slots=True)\nclass ReadSourceCommand: ...\n",
    ),
    Case(Rule.ADAPTER_NAMES, "adapters/outbound/hyperliquid/user_state.py", "class UserState: ...\n"),
    Case(Rule.NO_GENERIC_FOLDERS, "domain/common/x.py", "X = 1\n"),
    Case(Rule.NO_GENERIC_FOLDERS, "adapters/outbound/utils/x.py", "X = 1\n"),
    Case(Rule.NO_ANY, "adapters/outbound/telegram/x.py", "from typing import Any\n"),
    Case(Rule.NO_ANY, "domain/x.py", "import typing\nX: typing.Any = 1\n"),
    Case(Rule.TYPE_IGNORE_EXPLAINED, "adapters/inbound/api/app.py", "api.openapi = openapi  # type: ignore\n"),
    Case(
        Rule.TYPE_IGNORE_EXPLAINED,
        "adapters/inbound/api/app.py",
        "api.openapi = openapi  # type: ignore[method-assign]\n",
    ),
    Case(Rule.CONFIGURATION_THROUGH_SOURCE, "adapters/outbound/telegram/x.py", "import os\nTOKEN = os.environ['T']\n"),
    Case(Rule.CONFIGURATION_THROUGH_SOURCE, "adapters/outbound/sqlalchemy/x.py", "from os import getenv\n"),
    Case(Rule.CONFIGURATION_THROUGH_SOURCE, "bootstrap.py", "def f():\n    return os.getenv('X')\n"),
    Case(Rule.CONFIGURATION_THROUGH_SOURCE, "adapters/outbound/json/x.py", "import tomllib\n"),
    Case(
        Rule.SETTINGS_IN_THEIR_FOLDER,
        "bootstrap.py",
        "from autotrading.adapters.outbound.sqlalchemy.configuration import _settings_of\n",
    ),
    Case(
        Rule.SETTINGS_IN_THEIR_FOLDER,
        "adapters/outbound/telegram/composition.py",
        "from autotrading.adapters.outbound.sqlalchemy.configuration import _SqlAlchemySettings\n",
    ),
    Case(
        Rule.SETTINGS_IN_THEIR_FOLDER,
        "adapters/outbound/sqlalchemy/tables.py",
        "from autotrading.adapters.outbound.sqlalchemy.configuration import _settings_of\n",
    ),
    Case(
        Rule.SETTINGS_IN_THEIR_FOLDER,
        "adapters/outbound/sqlalchemy/database.py",
        "from autotrading.adapters.configuration.source import ConfigurationSource\n",
    ),
    Case(Rule.SETTINGS_IN_THEIR_FOLDER, "adapters/outbound/sqlalchemy/database.py", SOURCE_IN_A_CONSTRUCTOR),
    Case(
        Rule.BOOTSTRAP_CONFIGURES_THROUGH_COMPOSITIONS,
        "bootstrap.py",
        "def wire(source: ConfigurationSource):\n    return SqlAlchemyDatabaseAdapter(source)\n",
    ),
    Case(
        Rule.BOOTSTRAP_CONFIGURES_THROUGH_COMPOSITIONS,
        "bootstrap.py",
        "def wire(configuration):\n    source = ConfigurationSource(configuration)\n    return source.value('X')\n",
    ),
    Case(
        Rule.BOOTSTRAP_CONFIGURES_THROUGH_COMPOSITIONS, "bootstrap.py", "def wire(c):\n    return c['DATABASE_HOST']\n"
    ),
    # ADR nessun-test-escluso-o-saltato: no test is skipped, none is left out of the pipeline.
    Case(Rule.NO_EXCLUDED_TESTS, "tests/integration/x/test_a.py", "def test_a():\n    pytest.skip('no file')\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "tests/unit/x/test_a.py", "@pytest.mark.skipif(True, reason='')\ndef test_a(): ...\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "tests/unit/x/test_a.py", "@pytest.mark.xfail\ndef test_a(): ...\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "tests/unit/x/test_a.py", "def test_a():\n    pytest.xfail('later')\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "tests/unit/x/test_a.py", "pytest.importorskip('prophet')\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "tests/unit/x/test_a.py", "from pytest import skip\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "tests/unit/x/test_a.py", "@mark.skip\ndef test_a(): ...\n"),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "tests/unit/x/test_a.py",
        "@pytest.mark.parametrize('x', [pytest.param(1, marks=pytest.mark.skip)])\ndef test_a(x): ...\n",
    ),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "tests/integration/hyperliquid/test_a.py",
        "pytestmark = pytest.mark.integration\n@pytest.mark.testnet_credentials\ndef test_a(): ...\n",
        CREDENTIALS_MARKER,
    ),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "tests/integration/hyperliquid/test_a.py",
        "pytestmark = [pytest.mark.integration, pytest.mark.testnet_credentials]\ndef test_a(): ...\n",
        CREDENTIALS_MARKER,
    ),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "tests/integration/hyperliquid/test_a.py",
        "@pytest.mark.testnet_credentials\nclass TestA:\n    def test_b(self): ...\n",
        CREDENTIALS_MARKER,
    ),
    Case(Rule.NO_EXCLUDED_TESTS, "specs/E0-x/F0.1-x/R0.1.2-x.feature", "@R0.1.2 @wip\nFunzionalità: X\n"),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "specs/E0-x/F0.1-x/R0.1.2-x.feature",
        "# language: it\nFunzionalità: X\n\n  @wip\n  Scenario: Y\n    Allora va\n",
    ),
    Case(Rule.NO_EXCLUDED_TESTS, PIPELINE_TEST_RUN, 'run: uv run pytest -m "not pipeline and not sources"\n'),
    Case(Rule.NO_EXCLUDED_TESTS, PIPELINE_TEST_RUN, "run: uv run pytest --deselect tests/x.py::test_a\n"),
    Case(Rule.NO_EXCLUDED_TESTS, PIPELINE_TEST_RUN, "run: uv run pytest --ignore=tests/integration\n"),
    Case(Rule.NO_EXCLUDED_TESTS, PIPELINE_TEST_RUN, 'run: uv run pytest -k "not live"\n'),
    Case(Rule.NO_EXCLUDED_TESTS, "dashboard/src/features/x/y.test.tsx", "it.skip('shows', () => {});\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "dashboard/src/features/x/y.test.tsx", "describe.only('a', () => {});\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "dashboard/src/features/x/y.test.tsx", "it.todo('later');\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "dashboard/src/features/x/y.test.tsx", "it.skipIf(slow)('a', () => {});\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "dashboard/e2e/layout/a.spec.ts", "test.fixme('x', async () => {});\n"),
    Case(Rule.NO_EXCLUDED_TESTS, "dashboard/e2e/layout/a.spec.ts", "test.describe.skip('x', () => {});\n"),
]

CLEAN = [
    Case(Rule.PORTS_IN_PORTS_MODULES, "application/flows/ports.py", "class ClockPort(Protocol): ...\n"),
    Case(Rule.PORT_NAMES, "application/orders/ports.py", "class ExchangePort(Protocol): ...\n"),
    Case(
        Rule.BOOTSTRAP_WITHOUT_DECISIONS,
        "bootstrap.py",
        'def wire(x: int | None) -> str | None:\n    return "a" + x.name\n',
    ),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "bootstrap.py", "def wire(x):\n    return [y for y in x]\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_DECISIONS, "adapters/outbound/rss/news.py", "def f(x):\n    return x or 1\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_CONSTANTS, "bootstrap.py", "import logging\ndef wire(): ...\n"),
    Case(Rule.BOOTSTRAP_WITHOUT_CLASSES, "bootstrap.py", "def wire(settings):\n    return Adapter(settings)\n"),
    Case(Rule.NO_BRIDGES, "adapters/outbound/sqlalchemy/x.py", "class SqlAlchemyAccountRepositoryAdapter: ...\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "adapters/outbound/sqlalchemy/x.py", "from sqlalchemy import Engine\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "adapters/outbound/hyperliquid/x.py", "from eth_account import Account\n"),
    Case(Rule.LIBRARIES_IN_THEIR_FOLDER, "domain/flows/flow.py", "from decimal import Decimal\nimport autotrading\n"),
    Case(Rule.ADAPTERS_DO_NOT_ORCHESTRATE, "adapters/outbound/sqlalchemy/x.py", CONTRACT_IMPORTS),
    Case(Rule.ADAPTERS_DO_NOT_ORCHESTRATE, "adapters/outbound/telegram/x.py", DECORATOR),
    Case(
        Rule.ADAPTERS_DO_NOT_ORCHESTRATE,
        "adapters/inbound/api/x.py",
        "from autotrading.application.orders.open_position import OpenPositionUseCase\n",
    ),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "adapters/outbound/threads/x.py", "import threading\n"),
    Case(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, "domain/flows/flow.py", "from datetime import UTC\n"),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "domain/orders/order.py", '"""Orders as Hyperliquid fills them."""\n'),
    Case(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, "adapters/outbound/hyperliquid/x.py", 'COIN = "USDC"\n'),
    Case(Rule.ONLY_PROJECT_EXCEPTIONS_RAISED, "domain/flows/flow.py", "def f():\n    raise FlowNotFoundError\n"),
    Case(
        Rule.ERROR_SHAPE,
        "domain/errors.py",
        "class AutotradingError(Exception): ...\nclass DomainError(AutotradingError): ...\n",
    ),
    Case(Rule.NO_GENERIC_EXCEPT, "adapters/outbound/rss/news.py", "try:\n    f()\nexcept httpx.HTTPError:\n    pass\n"),
    Case(
        Rule.USE_CASE_SHAPE,
        "application/flows/create_flow.py",
        "class CreateFlowUseCase:\n    def execute(self): ...\n",
    ),
    Case(
        Rule.COMMAND_SHAPE,
        "application/flows/create_flow.py",
        "@dataclass(frozen=True, slots=True)\nclass CreateFlowCommand: ...\nclass CreateFlowUseCase: ...\n",
    ),
    Case(
        Rule.ADAPTER_NAMES,
        "adapters/outbound/hyperliquid/x.py",
        "class HyperliquidExchangeAdapter: ...\nclass HyperliquidShapeError(AdapterError): ...\nclass _State: ...\n",
    ),
    Case(Rule.NO_GENERIC_FOLDERS, "domain/flows/flow.py", "X = 1\n"),
    Case(Rule.NO_ANY, "domain/x.py", "from typing import Protocol\nX: object = 1\n"),
    Case(
        Rule.TYPE_IGNORE_EXPLAINED,
        "adapters/inbound/api/app.py",
        "# FastAPI documents this override.\napi.openapi = openapi  # type: ignore[method-assign]\n",
    ),
    Case(
        Rule.TYPE_IGNORE_EXPLAINED,
        "adapters/inbound/api/app.py",
        "api.openapi = openapi  # type: ignore[method-assign]  # FastAPI documents this override\n",
    ),
    Case(
        Rule.CONFIGURATION_THROUGH_SOURCE,
        "adapters/configuration/source.py",
        "import os\nPROCESS_ENVIRONMENT = os.environ\n",
    ),
    Case(
        Rule.CONFIGURATION_THROUGH_SOURCE, "adapters/outbound/json/x.py", "import os\nPATH = os.path.join('a', 'b')\n"
    ),
    Case(
        Rule.SETTINGS_IN_THEIR_FOLDER,
        "adapters/outbound/sqlalchemy/composition.py",
        "from autotrading.adapters.configuration.source import ConfigurationSource\n"
        "from autotrading.adapters.outbound.sqlalchemy.configuration import _settings_of\n",
    ),
    Case(
        Rule.SETTINGS_IN_THEIR_FOLDER,
        "adapters/outbound/sqlalchemy/configuration.py",
        "from autotrading.adapters.configuration.errors import InvalidConfigurationError\n"
        "from autotrading.adapters.configuration.source import ConfigurationSource\n",
    ),
    Case(
        Rule.SETTINGS_IN_THEIR_FOLDER,
        "adapters/outbound/sqlalchemy/database.py",
        "class SqlAlchemyDatabaseAdapter:\n    def __init__(self, host: str, port: int) -> None: ...\n",
    ),
    Case(Rule.BOOTSTRAP_CONFIGURES_THROUGH_COMPOSITIONS, "bootstrap.py", BOOTSTRAP_COMPOSITION),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "tests/integration/hyperliquid/test_a.py",
        "pytestmark = pytest.mark.integration\n@pytest.mark.parametrize('x', [1])\ndef test_a(x): ...\n",
        CREDENTIALS_MARKER,
    ),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "tests/integration/x/test_a.py",
        "def test_a(cycle, path):\n    assert cycle.skipped()\n    path.skip()\n    pytest.fail('no file')\n",
    ),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "specs/E4-x/F4.1-x/R4.1.2-x.feature",
        "# language: it\nFunzionalità: X\n  oggi @wip perché manca\n\n  @pipeline\n  Scenario: Y\n    Allora va\n",
    ),
    Case(Rule.NO_EXCLUDED_TESTS, PIPELINE_TEST_RUN, 'run: uv run pytest --cov -m "not pipeline"\n'),
    Case(
        Rule.NO_EXCLUDED_TESTS,
        "dashboard/src/features/x/y.test.tsx",
        "it('says a skipped cycle never started', () => {});\nconst skipped = test.step('a');\n",
    ),
]


@pytest.mark.parametrize("case", VIOLATING, ids=str)
def test_rule_catches_the_violation(case: Case) -> None:
    caught = [violation for violation in case.violations if violation.rule is case.rule]

    assert caught


@pytest.mark.parametrize("case", CLEAN, ids=str)
def test_rule_leaves_compliant_code_alone(case: Case) -> None:
    caught = [violation for violation in case.violations if violation.rule is case.rule]

    assert not caught


def test_violation_names_file_line_rule_and_where_the_code_goes() -> None:
    module = SourceModule.parse("bootstrap.py", "def wire(x):\n    return x or 0\n")

    description = violations_of(module)[0].describe()

    assert description.startswith("src/autotrading/bootstrap.py:2 [bootstrap-senza-decisioni] BoolOp in wire -> ")
    assert "domain o in un caso d'uso" in description


def test_every_rule_has_a_violating_example() -> None:
    assert {case.rule for case in VIOLATING} == set(Rule)


def test_every_rule_has_a_compliant_example() -> None:
    assert {case.rule for case in CLEAN} == set(Rule)


def test_a_test_with_a_marker_the_pipeline_leaves_out_is_named_by_its_identifier() -> None:
    source = "@pytest.mark.testnet_credentials\nclass TestA:\n    def test_b(self): ...\n    def helper(self): ...\n"

    caught = violations_of_file("tests/integration/x/test_a.py", source, CREDENTIALS_MARKER)

    assert [violation.location for violation in caught] == ["tests/integration/x/test_a.py:TestA.test_b"]


def test_an_excluded_marker_is_named_by_the_marker() -> None:
    caught = violations_of_file(PIPELINE_TEST_RUN, 'run: >-\n  uv run pytest\n  -m "not pipeline and not slow"\n')

    assert [(violation.location, violation.line) for violation in caught] == [(f"{PIPELINE_TEST_RUN}:slow", 3)]


@pytest.mark.parametrize(
    ("action", "excluded"),
    [
        ('run: uv run pytest -m "not pipeline and not testnet_credentials"\n', {"pipeline", "testnet_credentials"}),
        ("run: uv run pytest --cov\n", set()),
    ],
)
def test_the_markers_the_pipeline_leaves_out_are_read(action: str, excluded: set[str]) -> None:
    assert pipeline_excluded_markers(action) == excluded


def test_a_violation_outside_the_source_names_its_path_from_the_root() -> None:
    (violation,) = violations_of_file("tests/unit/x/test_a.py", "def test_a():\n    pytest.skip('no')\n")

    assert violation.describe().startswith("tests/unit/x/test_a.py:2 [nessun-test-escluso] pytest.skip in test_a -> ")


def test_a_source_module_read_from_the_root_keeps_its_rules() -> None:
    caught = violations_of_file(f"{SOURCE_PREFIX}bootstrap.py", "def wire(x):\n    return x or 0\n")

    assert [violation.rule for violation in caught] == [Rule.BOOTSTRAP_WITHOUT_DECISIONS]


def test_a_file_no_rule_reads_has_no_violation() -> None:
    assert violations_of_file("docs/adr/x.md", "it.skip('a')\n") == []
