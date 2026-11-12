from datetime import UTC, datetime, time

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.sources.source_sample import CycleReference, SourceValue
from tests.support.source_collection import SourceCycle
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.8-valori-raccolti-registrati.feature")

DAY = datetime(2026, 11, 12, tzinfo=UTC).date()


def at(clock: str) -> datetime:
    return datetime.combine(DAY, time.fromisoformat(clock), UTC)


@pytest.fixture
def cycle() -> SourceCycle:
    return SourceCycle()


@pytest.fixture
def cycles() -> dict[str, CycleReference]:
    return {}


@given(quoted('che "{user}" ha il flusso "{flow}" con asset "{asset}" e la fonte "{source}" attiva'))
def flow_with_asset(cycle: SourceCycle, asset: str, source: str) -> None:
    cycle.assets = (asset,)
    cycle.activate(source)


@given(quoted('che "{user}" ha il flusso "{flow}" con la fonte "{source}" attiva'))
def flow_with_source(cycle: SourceCycle, source: str) -> None:
    cycle.assets = ("BTC",)
    cycle.activate(source)


@given(quoted('che l\'ultima candela a 15 minuti di "{asset}" chiude alle {clock}'))
def last_candle(cycle: SourceCycle, clock: str) -> None:
    cycle.readers["indicatori"].values = [SourceValue(at(clock), {"prezzo": "100"})]


@given(quoted("che una notizia è stata pubblicata alle {clock}"))
def published_story(cycle: SourceCycle, clock: str) -> None:
    cycle.readers["notizie"].values = [SourceValue(at(clock), {"titolo": "Bitcoin"})]


@when(quoted('il flusso "{flow}" esegue alle {clock} il ciclo "{name}"'))
def run_cycle(cycle: SourceCycle, cycles: dict[str, CycleReference], clock: str, name: str) -> None:
    cycles[name] = cycle.run(at(clock))


@then(quoted('i valori della fonte "{source}" per "{asset}" sono registrati con istante di riferimento {clock}'))
def recorded_reference(cycle: SourceCycle, source: str, asset: str, clock: str) -> None:
    recorded = [(sample.source, sample.asset, sample.reference_at) for sample in cycle.samples.samples]
    assert recorded == [(source, asset, at(clock))]


@then(quoted("con istante di raccolta {clock}"))
def recorded_collection(cycle: SourceCycle, clock: str) -> None:
    assert [sample.collected_at for sample in cycle.samples.samples] == [at(clock)]


@then(quoted('con il ciclo "{name}" del flusso "{flow}"'))
def recorded_cycle(cycle: SourceCycle, cycles: dict[str, CycleReference], name: str) -> None:
    assert [sample.cycle for sample in cycle.samples.samples] == [cycles[name]]
    assert cycles[name].flow_id == cycle.flow_id


@then(quoted("la notizia è registrata con istante di riferimento {reference} e istante di raccolta {collected}"))
def story_recorded(cycle: SourceCycle, reference: str, collected: str) -> None:
    recorded = [
        (sample.source, sample.asset, sample.reference_at, sample.collected_at) for sample in cycle.samples.samples
    ]
    assert recorded == [("notizie", None, at(reference), at(collected))]
