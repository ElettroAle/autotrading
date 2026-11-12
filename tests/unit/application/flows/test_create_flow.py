import logging
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.create_flow import CreateFlowCommand, CreateFlowUseCase, FlowChecks, SourceRequest
from autotrading.application.flows.errors import (
    AssetNotTradableError,
    FlowAccountNotFoundError,
    FlowExchangeUnavailableError,
    FlowNameInUseError,
    InvalidFlowSettingError,
)
from autotrading.application.flows.free_capital import ReadFreeCapitalCommand, ReadFreeCapitalUseCase
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.errors import (
    CapitalAboveFreeCapitalError,
    CycleIntervalOutOfRangeError,
    FlowNameRequiredError,
    MaxLeverageRequiredError,
)
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_account import FakeFlowAccountAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.markets import FakeMarketsAdapter
from tests.fakes.model_settings import FakeModelSettingsAdapter
from tests.fakes.source_settings import FakeSourceSettingsAdapter
from tests.support.flows import a_configuration, a_flow

MODEL = "openrouter/deepseek-chat"


class Flows:
    """The use cases of the flows of one tenant, on the fake adapters."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.accounts = FakeFlowAccountAdapter()
        self.account_id = uuid4()
        self.accounts.add(self.account_id, Decimal(1000))
        self.markets = FakeMarketsAdapter()
        self.models = FakeModelSettingsAdapter(MODEL)
        checks = FlowChecks(
            self.accounts, {"Hyperliquid": self.markets}, self.models, FakeSourceSettingsAdapter("notizie")
        )
        self.create = CreateFlowUseCase(self.tenant_id, self.repository, checks)

    def command(self, **changes: object) -> CreateFlowCommand:
        command = CreateFlowCommand(
            name="alfa",
            account_id=self.account_id,
            assets=("btc", "ETH"),
            model=MODEL,
            allocated_capital=Decimal(400),
            max_leverage=5,
            max_margin_exposure_percent=Decimal(10),
        )
        return replace(command, **changes)  # type: ignore[arg-type]  # each test names the fields it changes


@pytest.fixture
def flows() -> Flows:
    return Flows()


def test_a_valid_flow_is_saved_stopped_with_its_whole_configuration(flows: Flows) -> None:
    command = flows.command(
        sources=(SourceRequest("notizie", 7, {"hours": 6}),), instructions="  prudente ", cycle_minutes=30
    )

    flow = flows.create.execute(command)

    assert flows.store.flows == [flow]
    assert (flow.tenant_id, flow.account_id, flow.name.value, flow.status) == (
        flows.tenant_id,
        flows.account_id,
        "alfa",
        FlowStatus.STOPPED,
    )
    configuration = flow.configuration
    assert (configuration.version, configuration.assets, configuration.cycle_interval.minutes) == (
        1,
        ("BTC", "ETH"),
        30,
    )
    assert configuration.model.name == MODEL
    assert [(source.name, source.weight, dict(source.parameters)) for source in configuration.sources] == [
        ("notizie", 7, {"hours": 6})
    ]
    assert configuration.instructions == "prudente"
    assert (configuration.risk_limits.max_leverage, configuration.allocated_capital) == (5, Decimal(400))


def test_the_creation_is_logged_with_the_flow_and_nothing_of_its_configuration(
    flows: Flows, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        flow = flows.create.execute(flows.command())

    assert [(record.getMessage(), getattr(record, "flow_id", None)) for record in caplog.records] == [
        ("flusso creato", str(flow.id.value))
    ]


def test_the_model_parameters_reach_the_model_settings(flows: Flows) -> None:
    flow = flows.create.execute(flows.command(model_parameters={"temperature": "0.5"}))

    assert flow.configuration.model.parameters == {"temperature": "0.5"}
    assert flows.models.asked == [MODEL]


@pytest.mark.parametrize(
    ("changes", "error", "reason"),
    [
        ({"name": " "}, FlowNameRequiredError, "nome del flusso obbligatorio"),
        ({"cycle_minutes": 0}, CycleIntervalOutOfRangeError, "intervallo di ciclo fuori da 1-1440 minuti"),
        ({"model": "openai/inesistente"}, InvalidFlowSettingError, "modello non disponibile: openai/inesistente"),
        ({"sources": (SourceRequest("oroscopo"),)}, InvalidFlowSettingError, "fonte non disponibile: oroscopo"),
        ({"max_leverage": None}, MaxLeverageRequiredError, "la leva massima è obbligatoria"),
        ({"assets": ("BTC", "XYZ", "ABC")}, AssetNotTradableError, "asset non negoziabile sull'exchange: XYZ, ABC"),
        ({"account_id": uuid4()}, FlowAccountNotFoundError, "conto non trovato"),
        (
            {"allocated_capital": Decimal("1000.01")},
            CapitalAboveFreeCapitalError,
            "capitale allocato oltre il capitale libero: 1000 USDC",
        ),
    ],
)
def test_an_invalid_configuration_is_refused_whole_with_the_reason(
    flows: Flows, changes: dict[str, object], error: type[AutotradingError], reason: str
) -> None:
    with pytest.raises(error) as raised:
        flows.create.execute(flows.command(**changes))

    assert str(raised.value) == reason
    assert flows.store.flows == []


def test_the_name_is_checked_before_the_configuration(flows: Flows) -> None:
    flows.create.execute(flows.command())

    with pytest.raises(FlowNameInUseError, match=r"^nome già usato da un altro flusso$"):
        flows.create.execute(flows.command(model="openai/inesistente"))

    assert flows.models.asked == [MODEL]


def test_the_name_of_an_archived_flow_can_be_used_again(flows: Flows) -> None:
    flows.store.flows.append(a_flow(flows.tenant_id, status=FlowStatus.ARCHIVED, account_id=flows.account_id))

    flows.create.execute(flows.command())

    assert [flow.status for flow in flows.store.flows] == [FlowStatus.ARCHIVED, FlowStatus.STOPPED]


def test_the_assets_are_tradable_only_on_an_exchange_with_markets(flows: Flows) -> None:
    flows.accounts.add(flows.account_id, Decimal(1000), exchange="Altro")

    with pytest.raises(AssetNotTradableError, match=r"^asset non negoziabile sull'exchange: BTC, ETH$"):
        flows.create.execute(flows.command())


def test_an_exchange_out_of_reach_refuses_the_creation(flows: Flows) -> None:
    flows.markets.reachable = False

    with pytest.raises(FlowExchangeUnavailableError, match=r"^exchange non raggiungibile, riprovare$"):
        flows.create.execute(flows.command())


def test_the_capital_of_the_other_flows_of_the_account_is_not_free(flows: Flows) -> None:
    flows.create.execute(flows.command(name="beta", assets=("SOL",), allocated_capital=Decimal(600)))
    other_account = a_flow(flows.tenant_id, name="gamma", configuration=a_configuration(allocated_capital=Decimal(900)))
    flows.store.flows.append(other_account)

    flows.create.execute(flows.command(assets=("BTC",), allocated_capital=Decimal(400)))

    with pytest.raises(CapitalAboveFreeCapitalError, match=r"^capitale allocato oltre il capitale libero: 0 USDC$"):
        flows.create.execute(flows.command(name="delta", assets=("ETH",), allocated_capital=Decimal("0.01")))


def test_the_free_capital_of_an_account_is_its_balance_less_its_flows(flows: Flows) -> None:
    flows.create.execute(flows.command(allocated_capital=Decimal(400)))
    flows.store.flows.append(a_flow(flows.tenant_id, name="altro", configuration=a_configuration()))

    free = ReadFreeCapitalUseCase(flows.repository, flows.accounts).execute(ReadFreeCapitalCommand(flows.account_id))

    assert free == FreeCapital(Decimal(600), "USDC")


def test_the_free_capital_of_an_unknown_account_is_not_found(flows: Flows) -> None:
    with pytest.raises(FlowAccountNotFoundError):
        ReadFreeCapitalUseCase(flows.repository, flows.accounts).execute(ReadFreeCapitalCommand(uuid4()))


def test_the_flows_are_listed_by_name(flows: Flows) -> None:
    for name in ("gamma", "alfa", "beta"):
        flows.store.flows.append(a_flow(flows.tenant_id, name=name))

    assert [flow.name.value for flow in ListFlowsUseCase(flows.repository).execute()] == ["alfa", "beta", "gamma"]
