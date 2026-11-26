"""R5.3.7: with the options of the memory on, every asset begins with the summary of the positions the flow closed on
it, by side, and gives the summary of the other assets of the flow; both off by default, and a flow saved before keeps
its version. On the cycle the worker composes and on the use cases of the API and of the MCP server, with the fake
adapters (ADR memoria-del-flusso-con-riepilogo-e-altri-asset).
"""

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from pytest_bdd import given, then, when

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.memory_entry import OTHER_ASSET, AssetMemory
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.flow_cycles import at
from tests.support.mcp_session import McpSession, body_of
from tests.support.steps import quoted
from tests.support.steps_r5_3_4 import USER, MemoryCycles
from tests.support.steps_r5_3_5 import *  # noqa: F403 - the steps of R5.3.4 and R5.3.5 these scenarios share
from tests.support.steps_r5_3_5 import MemoryImprovements, creates_without_the_new_settings

ASSETS = ("NEAR", "SUI")
TODAY, YESTERDAY = "oggi", "ieri"
FEES = Decimal("0.1")
SWITCHED_ON = "acceso"
# Every closing of the scenarios is the position an opening of the flow opened half an hour before.
OPENED_BEFORE = timedelta(minutes=30)


@dataclass
class MemorySummaries:
    """The memory cycles of R5.3.4 and R5.3.5, with the closings recorded and what the tools of the MCP server read."""

    improvements: MemoryImprovements
    closings: int = 0
    version_before: int = 0
    mcp_flow: dict[str, Any] = field(default_factory=dict)
    mcp_memory: dict[str, Any] = field(default_factory=dict)

    @property
    def memory(self) -> MemoryCycles:
        return self.improvements.memory

    def ensure_flow(self, name: str) -> None:
        """The flow of anna on NEAR and SUI, unless the scenario has made it already."""
        if name not in self.memory.cycles.users:
            self.memory.cycles.add_flow(USER, name, assets=ASSETS)

    def memory_of(self, name: str) -> FlowMemory:
        return self.memory.flow(name).configuration.memory

    def closed(self, name: str, asset: str, net_pnl: Decimal, day: str = TODAY) -> None:
        """A short of the flow on the asset closed on the day with the result after the fees given, opened by an
        opening of the flow half an hour before; every closing a few minutes after the one before.
        """
        flow = self.memory.flow(name)
        self.closings += 1
        midday = at("08:00") if day == TODAY else at("15:00") - timedelta(days=1)
        closed_at = midday + timedelta(minutes=5 * self.closings)
        opened_at = closed_at - OPENED_BEFORE
        decision = RecordedDecision(asset, DecisionAction.OPEN, TradeSide.SHORT, 70, motive_of(asset, self.closings))
        self.memory.decided(name, opened_at, decision)
        self.memory.cycles.platform.closed_positions.positions.append(
            ClosedPosition(
                tenant_id=flow.tenant_id,
                flow_id=flow.id,
                asset=asset,
                side=TradeSide.SHORT,
                leverage=2,
                margin=Decimal(50),
                opening=PositionEnd(Decimal(3), opened_at, opened_at),
                closing=PositionEnd(Decimal(3), closed_at),
                fees=FEES,
                reason=CloseReason.AGENT,
                realized_pnl=net_pnl + FEES,
            )
        )

    def received_on(self, asset: str) -> AssetMemory:
        return asset_memory_of(self.memory.received("alfa"), asset)


@pytest.fixture
def summaries(improvements: MemoryImprovements) -> MemorySummaries:
    return MemorySummaries(improvements)


def motive_of(asset: str, closing: int) -> str:
    return f"tesi short {closing} su {asset}"


def amount_of(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def asset_memory_of(memory: tuple[AssetMemory, ...] | None, asset: str) -> AssetMemory:
    assert memory is not None
    [remembered] = [each for each in memory if each.asset == asset]
    return remembered


def block_of(system: str, asset: str) -> str:
    """The block of the asset in the memory of the system prompt, up to the next asset."""
    start = system.index(f"\n{asset}:\n") + 1
    following = [system.find(f"\n{other}:\n", start) for other in ASSETS if other != asset]
    ends = [end for end in following if end > start]
    return system[start : min(ends, default=len(system))]


# Given


@given(
    quoted(
        'che "{user}" ha il flusso "{flow}" attivo con asset "{first}" e "{second}" e la memoria attiva con {days}'
        " giorni"
    )
)
def flow_with_two_assets(  # noqa: PLR0917 - one argument per value of the step
    summaries: MemorySummaries, user: str, flow: str, first: str, second: str, days: str
) -> None:
    assert (user, (first, second)) == (USER, ASSETS)
    summaries.ensure_flow(flow)
    summaries.memory.remember(flow, FlowMemory(active=True, days=int(days)))


@given(quoted('che "{flow}" ha chiuso su "{asset}" queste posizioni short, con PnL al netto delle commissioni:'))
def closed_these(summaries: MemorySummaries, flow: str, asset: str, datatable: list[list[str]]) -> None:
    for day, pnl in datatable[1:]:
        summaries.closed(flow, asset, amount_of(pnl), day.strip())


@given(quoted('che "{flow}" ha chiuso oggi su "{asset}" una posizione short con PnL netto {pnl} USDC'))
def closed_one_today(summaries: MemorySummaries, flow: str, asset: str, pnl: str) -> None:
    summaries.closed(flow, asset, amount_of(pnl))


@given(quoted('che "{flow}" ha chiuso oggi su "{asset}" un\'altra posizione short con PnL netto {pnl} USDC'))
def closed_another_today(summaries: MemorySummaries, flow: str, asset: str, pnl: str) -> None:
    summaries.closed(flow, asset, amount_of(pnl))


@given(quoted('che "{flow}" ha chiuso oggi una posizione short su "{asset}" con PnL netto {pnl} USDC'))
def closed_a_short_today(summaries: MemorySummaries, flow: str, asset: str, pnl: str) -> None:
    summaries.closed(flow, asset, amount_of(pnl))


@given(quoted('che la memoria di "{flow}" ha il riepilogo {state}'))
def summary_switched(summaries: MemorySummaries, flow: str, state: str) -> None:
    summaries.memory.remember(flow, summaries.memory_of(flow).changed(summary=state == SWITCHED_ON))


@given(quoted('che la memoria di "{flow}" ha il riepilogo acceso e {decisions} decisioni'))
def summary_with_decisions(summaries: MemorySummaries, flow: str, decisions: str) -> None:
    summaries.memory.remember(flow, summaries.memory_of(flow).changed(summary=True, decisions=int(decisions)))


@given(quoted('che la memoria di "{flow}" ha gli altri asset accesi e il riepilogo spento'))
def other_assets_alone(summaries: MemorySummaries, flow: str) -> None:
    summaries.memory.remember(flow, summaries.memory_of(flow).changed(summary=False, other_assets=True))


@given(quoted('che la memoria di "{flow}" ha il riepilogo spento e gli altri asset spenti'))
def both_options_off(summaries: MemorySummaries, flow: str) -> None:
    summaries.memory.remember(flow, summaries.memory_of(flow).changed(summary=False, other_assets=False))


@given(quoted('che il flusso "{flow}" ha la memoria attiva con il riepilogo acceso'))
def memory_with_summary(summaries: MemorySummaries, flow: str) -> None:
    summaries.ensure_flow(flow)
    summaries.memory.remember(flow, FlowMemory(active=True, summary=True))


@given(quoted('che il flusso "{flow}" esisteva prima delle nuove opzioni, con la memoria attiva'))
def flow_from_before_the_options(summaries: MemorySummaries, flow: str) -> None:
    # A version saved before the options knew every other part of the memory, and reads as its document had them.
    saved = FlowMemory(active=True, decisions=10, days=30, text_length=160, all_decisions=False)
    summaries.memory.remember(flow, saved)
    summaries.version_before = summaries.memory.flow(flow).configuration.version


# When


@when(quoted('"{user}" crea un flusso senza indicare le opzioni riepilogo e altri asset della memoria'))
def creates_without_the_options(summaries: MemorySummaries, user: str) -> None:
    creates_without_the_new_settings(summaries.improvements, user)


@when(quoted('il client MCP di "{user}" accende il riepilogo della memoria di "{flow}"'))
def mcp_switches_the_summary_on(summaries: MemorySummaries, user: str, flow: str) -> None:
    """On the flow of anna with the memory on and a short closed today on NEAR."""
    summaries.ensure_flow(flow)
    summaries.memory.remember(flow, FlowMemory(active=True))
    summaries.closed(flow, "NEAR", Decimal("-2.40"))
    platform = summaries.memory.cycles.platform
    platform.now = summaries.memory.cycles.clock.now()
    flow_id = str(summaries.memory.flow(flow).id.value)
    mcp = McpSession(platform)
    arguments = {"flow_id": flow_id, "modification": {"memory": {"summary": True}}}
    result = mcp.call_as(user, "modify_flow", arguments)
    assert not result.is_error, body_of(result)
    summaries.mcp_flow = body_of(mcp.call_as(user, "get_flow", {"flow_id": flow_id}))
    summaries.mcp_memory = body_of(mcp.call_as(user, "read_flow_memory", {"flow_id": flow_id}))


# Then


@then("la memoria del flusso ha il riepilogo spento e gli altri asset spenti")
def created_with_both_off(summaries: MemorySummaries) -> None:
    created = summaries.improvements.created
    assert created is not None
    assert (created.configuration.memory.summary, created.configuration.memory.other_assets) == (False, False)


@then(quoted('la memoria di "{flow}" ha il riepilogo spento e gli altri asset spenti'))
def read_with_both_off(summaries: MemorySummaries, flow: str) -> None:
    read = summaries.improvements.read
    assert read is not None
    assert read.name.value == flow
    assert read.configuration.memory.active is True
    assert (read.configuration.memory.summary, read.configuration.memory.other_assets) == (False, False)


@then(quoted('la configurazione di "{flow}" resta alla stessa versione'))
def same_version(summaries: MemorySummaries, flow: str) -> None:
    read = summaries.improvements.read
    assert read is not None
    assert read.configuration.version == summaries.version_before
    assert summaries.memory.flow(flow).configuration.version == summaries.version_before


@then(quoted('vede in testa alla memoria di "{asset}" la riga di riepilogo come la riceve l\'agente'))
def summary_read_as_received(summaries: MemorySummaries, asset: str) -> None:
    remembered = asset_memory_of(summaries.memory.remembered, asset)
    assert remembered.summary == (
        f"{asset} short — oggi: 1 chiuse, 0 vinte, 1 perse, PnL -2,40 USDC;"
        " ultimi 30 giorni: 1 chiuse, 0 vinte, 1 perse, PnL -2,40 USDC",
    )
    assert remembered.lines[0] == remembered.summary[0]
    summaries.memory.cycles.run("alfa")
    assert summaries.received_on(asset) == remembered


@then(quoted('la memoria di "{asset}" comincia con "{line}"'))
def begins_with(summaries: MemorySummaries, asset: str, line: str) -> None:
    remembered = summaries.received_on(asset)
    assert remembered.summary == (line,)
    assert remembered.lines[0] == line
    assert block_of(summaries.memory.cycles.system_text(), asset).startswith(f"{asset}:\n- {line}\n")


@then(quoted('dopo la riga seguono le decisioni su "{asset}" come oggi'))
def decisions_follow(summaries: MemorySummaries, asset: str) -> None:
    remembered = summaries.received_on(asset)
    expected = [motive_of(asset, closing) for closing in (3, 2, 1, 5, 4)]
    assert [entry.motive for entry in remembered.entries] == expected
    assert remembered.lines == (*remembered.summary, *(entry.text for entry in remembered.entries))
    block = block_of(summaries.memory.cycles.system_text(), asset)
    assert block == "\n".join((f"{asset}:", *(f"- {line}" for line in remembered.lines)))


@then(quoted('la memoria di "{asset}" non ha una riga di riepilogo per long'))
def no_long_line(summaries: MemorySummaries, asset: str) -> None:
    remembered = summaries.received_on(asset)
    assert [line.split(" — ")[0] for line in remembered.summary] == [f"{asset} short"]
    assert f"- {asset} long —" not in summaries.memory.cycles.system_text()


@then(quoted('la memoria di "{asset}" riporta tra gli altri asset "{line}"'))
def other_asset_line(summaries: MemorySummaries, asset: str, line: str) -> None:
    remembered = summaries.received_on(asset)
    assert remembered.other_assets == (line,)
    assert f"\n- {OTHER_ASSET}{line}\n" in block_of(summaries.memory.cycles.system_text(), asset)


@then(quoted('la memoria di "{asset}" non riporta le decisioni su "{other}"'))
def no_decision_of_the_other(summaries: MemorySummaries, asset: str, other: str) -> None:
    remembered = summaries.received_on(asset)
    assert remembered.entries
    assert {entry.asset for entry in remembered.entries} == {asset}
    assert summaries.received_on(other).entries
    assert motive_of(other, 6) not in block_of(summaries.memory.cycles.system_text(), asset)


@then(quoted('la memoria di "{asset}" non comincia con una riga di riepilogo di "{same}"'))
def no_own_summary(summaries: MemorySummaries, asset: str, same: str) -> None:
    remembered = summaries.received_on(asset)
    assert asset == same
    assert remembered.summary == ()
    assert remembered.lines[0].startswith(OTHER_ASSET)
    assert block_of(summaries.memory.cycles.system_text(), asset).startswith(f"{asset}:\n- {OTHER_ASSET}")


@then(quoted('la memoria di "{asset}" contiene solo le decisioni su "{same}", come oggi'))
def only_the_decisions(summaries: MemorySummaries, asset: str, same: str) -> None:
    remembered = summaries.received_on(asset)
    assert asset == same
    assert (remembered.summary, remembered.other_assets) == ((), ())
    assert len(remembered.entries) == 5
    assert {entry.asset for entry in remembered.entries} == {asset}
    block = block_of(summaries.memory.cycles.system_text(), asset)
    assert block == "\n".join((f"{asset}:", *(f"- {entry.text}" for entry in remembered.entries)))


@then(quoted('il dettaglio di "{flow}" letto dagli strumenti riporta la memoria con il riepilogo acceso'))
def mcp_flow_with_summary(summaries: MemorySummaries, flow: str) -> None:
    assert summaries.mcp_flow["name"] == flow
    assert summaries.mcp_flow["memory"]["summary"] is True
    assert summaries.mcp_flow["memory"]["other_assets"] is False
    assert summaries.memory.flow(flow).configuration.memory.summary is True


@then(quoted('la memoria di "{flow}" letta dagli strumenti mostra le righe di riepilogo come le riceve l\'agente'))
def mcp_memory_as_received(summaries: MemorySummaries, flow: str) -> None:
    [near] = [each for each in summaries.mcp_memory["assets"] if each["asset"] == "NEAR"]
    assert near["summary"] == [
        "NEAR short — oggi: 1 chiuse, 0 vinte, 1 perse, PnL -2,40 USDC;"
        " ultimi 30 giorni: 1 chiuse, 0 vinte, 1 perse, PnL -2,40 USDC"
    ]
    summaries.memory.cycles.run(flow)
    assert list(summaries.received_on("NEAR").summary) == near["summary"]
