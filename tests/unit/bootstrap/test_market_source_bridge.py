"""The bridge of the sources reads the indicators on the cycle interval of the flow in force (ADR 0057)."""

from dataclasses import replace

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from tests.support.flow_cycles import FlowCycles


def hourly(configuration: FlowConfiguration) -> FlowConfiguration:
    return replace(configuration, cycle_interval=CycleInterval(60))


def test_the_short_timeframe_is_the_cycle_interval_of_the_flow() -> None:
    world = FlowCycles()
    world.add_flow("anna", "alfa", sources=("indicatori",))
    world.reconfigure("alfa", hourly)

    world.run("alfa")

    [values] = world.sources_in_context("indicatori", "BTC")
    assert values["breve.timeframe"] == "1h"
    assert ("BTC", "1h", 110) in world.market.requests
