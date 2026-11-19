"""ADR-prova-di-un-adapter-di-fonte-nel-worker: the trial of an adapter of a source runs in the worker with the readers
of the cycle and records nothing; the API only asks the worker through its port and never opens the credentials.
"""

import ast
import json
import typing
from pathlib import Path

import pytest

from autotrading.adapters.outbound.worker import source_trial
from autotrading.application.sources import collect_cycle_source, ports, request_source_trial, try_source_adapter
from autotrading.domain.flows.cycle_interval import DEFAULT_CYCLE_INTERVAL
from tests.support.architecture import SOURCE_ROOT

ROOT = Path(SOURCE_ROOT)
BOOTSTRAP = ROOT / "bootstrap.py"
WORKER_API = ROOT / "adapters" / "inbound" / "api" / "worker.py"
OPENAPI = Path(__file__).resolve().parents[2] / "dashboard" / "openapi.json"
API_TRIAL = "/sources/{name}/adapters/{adapter}/trials"
WORKER_TRIAL = "/tenants/{tenant_id}/sources/{source}/adapters/{adapter}/trials"
RECORDING = ("CollectSourceUseCase", "SampleRepositoryPort")
SHARED_READERS = "readers_of"
TRIAL = "TrySourceAdapterUseCase"
API_FACTORIES = ("create_application", "tenant_use_cases")
WORKER_FACTORY = "worker_use_cases"


def names_of(source: str) -> set[str]:
    """Every name and attribute a module mentions, imports included."""
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    return names | attributes | imported


def called(source: str) -> set[str]:
    """The names of the functions a module calls."""
    calls = [node.func for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    return {call.id for call in calls if isinstance(call, ast.Name)}


def recording_names(source: str) -> set[str]:
    """The names of the recording of the samples a module mentions: a trial must name none."""
    return names_of(source) & set(RECORDING)


def names_in_functions(source: str) -> dict[str, set[str]]:
    """Every name each function of the bootstrap mentions, by the name of the function."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return {
        function.name: {node.id for node in ast.walk(function) if isinstance(node, ast.Name)} for function in functions
    }


def api_runs_the_trial(source: str) -> bool:
    """Whether a factory of the API builds the trial itself instead of asking the worker."""
    names = names_in_functions(source)
    return any(TRIAL in names.get(factory, set()) for factory in API_FACTORIES)


def source_of(module: object) -> str:
    return Path(str(getattr(module, "__file__", ""))).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("source", "recording"),
    [
        ("from autotrading.application.sources.collect_source import CollectSourceUseCase\n", {"CollectSourceUseCase"}),
        ("def read(samples: SampleRepositoryPort) -> None:\n    samples.add(value)\n", {"SampleRepositoryPort"}),
        ("from autotrading.application.sources.source_readers import readers_of\n", set()),
    ],
)
def test_adr_prova_di_un_adapter_di_fonte_nel_worker_a_trial_that_records_is_found(
    source: str, recording: set[str]
) -> None:
    assert recording_names(source) == recording


def test_adr_prova_di_un_adapter_di_fonte_nel_worker_the_trial_records_no_sample() -> None:
    assert recording_names(source_of(try_source_adapter)) == set()


def test_adr_prova_di_un_adapter_di_fonte_nel_worker_cycle_and_trial_share_the_readers() -> None:
    assert SHARED_READERS in called(source_of(try_source_adapter))
    assert SHARED_READERS in called(source_of(collect_cycle_source))


def test_adr_prova_di_un_adapter_di_fonte_nel_worker_a_request_may_belong_to_no_flow() -> None:
    flow_id = typing.get_type_hints(ports.SourceRequest)["flow_id"]

    assert type(None) in typing.get_args(flow_id)


@pytest.mark.parametrize(
    ("source", "runs"),
    [
        (f"def {API_FACTORIES[0]}(source):\n    trial = {TRIAL}(systems)\n", True),
        (f"def {API_FACTORIES[1]}(engine, trial: {TRIAL}):\n    return engine\n", True),
        (f"def {WORKER_FACTORY}(source):\n    trial = {TRIAL}(systems)\n", False),
    ],
)
def test_adr_prova_di_un_adapter_di_fonte_nel_worker_an_api_that_runs_the_trial_is_found(
    source: str, runs: bool
) -> None:
    assert api_runs_the_trial(source) is runs


def test_adr_prova_di_un_adapter_di_fonte_nel_worker_only_the_worker_runs_the_trial() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")

    assert not api_runs_the_trial(source)
    assert TRIAL in names_in_functions(source)[WORKER_FACTORY]


def test_adr_prova_di_un_adapter_di_fonte_nel_worker_the_api_asks_the_worker_through_its_port() -> None:
    names = names_of(source_of(request_source_trial))

    assert "SourceTrialPort" in names
    assert "OpenSourceCredentialsUseCase" not in names
    assert TRIAL not in names


def test_adr_prova_di_un_adapter_di_fonte_nel_worker_both_services_expose_the_trial() -> None:
    api_paths = json.loads(OPENAPI.read_text(encoding="utf-8"))["paths"]

    assert API_TRIAL in api_paths
    assert f'"{WORKER_TRIAL}"' in WORKER_API.read_text(encoding="utf-8")


def test_adr_prova_di_un_adapter_di_fonte_nel_worker_the_client_waits_longer_than_the_source() -> None:
    assert DEFAULT_CYCLE_INTERVAL.source_wait.total_seconds() < source_trial.TIMEOUT_SECONDS
