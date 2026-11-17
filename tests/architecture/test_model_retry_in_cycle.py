"""ADR-ritentativo-del-modello-nel-ciclo: a temporary failure of the model is asked again in the same cycle by
`AskAgentUseCase`, waiting through `PausePort`; the adapters of the model call never ask again and never wait, and
only the system clock waits on the machine.
"""

import ast
import inspect

from autotrading.application.agent.ask_agent import RETRY_PAUSES_SECONDS, AskAgentUseCase
from autotrading.application.agent.ports import PausePort
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

MODEL_CALLS = ("adapters/outbound/litellm/model_call.py", "adapters/outbound/openrouter/model_call.py")
PAUSE_ADAPTER = "adapters/outbound/system_clock/pause.py"


def waiting_modules(modules: list[SourceModule]) -> list[str]:
    """The modules that wait on the machine: a call to `sleep`, whatever module it comes from."""
    return sorted(
        {
            module.path
            for module in modules
            for node in ast.walk(module.tree)
            if isinstance(node, ast.Call) and _called_name(node) == "sleep"
        }
    )


def asking_again(module: SourceModule) -> list[str]:
    """The methods of the adapter classes that loop: a model call adapter makes one call per call it is asked."""
    return sorted(
        f"{module.path}:{method.name}"
        for node in module.tree.body
        if isinstance(node, ast.ClassDef)
        for method in node.body
        if isinstance(method, ast.FunctionDef)
        and any(isinstance(inner, (ast.For, ast.While)) for inner in ast.walk(method))
    )


def _called_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def test_adr_ritentativo_del_modello_nel_ciclo_only_the_system_clock_waits() -> None:
    assert waiting_modules(source_modules(SOURCE_ROOT)) == [PAUSE_ADAPTER]


def test_adr_ritentativo_del_modello_nel_ciclo_waiting_elsewhere_is_a_violation() -> None:
    use_case = SourceModule.parse("application/agent/ask_agent.py", "import time\n\ndef again():\n    time.sleep(5)\n")

    assert waiting_modules([use_case]) == ["application/agent/ask_agent.py"]


def test_adr_ritentativo_del_modello_nel_ciclo_the_model_call_adapters_never_ask_again() -> None:
    modules = [module for module in source_modules(SOURCE_ROOT) if module.path in MODEL_CALLS]

    assert [module.path for module in modules] == list(MODEL_CALLS)
    assert [found for module in modules for found in asking_again(module)] == []


def test_adr_ritentativo_del_modello_nel_ciclo_a_model_call_adapter_asking_again_is_a_violation() -> None:
    adapter = SourceModule.parse(
        MODEL_CALLS[1],
        "class OpenRouterModelCallAdapter:\n"
        "    def call(self):\n"
        "        for attempt in range(3):\n"
        "            return self._complete()\n",
    )

    assert asking_again(adapter) == [f"{MODEL_CALLS[1]}:call"]


def test_adr_ritentativo_del_modello_nel_ciclo_the_use_case_waits_through_its_port_twice() -> None:
    parameters = inspect.signature(AskAgentUseCase.__init__).parameters

    assert parameters["pause"].annotation is PausePort
    assert RETRY_PAUSES_SECONDS == (5.0, 15.0)
