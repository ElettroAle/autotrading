"""ADR-errore-di-openrouter-nella-risposta: the error OpenRouter puts in an answer is the reason of the failure. The
generic unexpected answer is built only where the answer has no body to read (`_complete`) or after the error of the
answer was read (`_unusable`), never straight from the reading of the answer.
"""

import ast

from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

MODEL_CALL = "adapters/outbound/openrouter/model_call.py"
GENERIC_REASON = "UNEXPECTED_ANSWER"
ALLOWED = {"_complete", "_unusable"}
ERROR_READER = "_error_of"


def generic_reasons(module: SourceModule) -> list[str]:
    """The functions and methods that give the generic reason, out of those allowed to."""
    return sorted(
        function.name
        for function in ast.walk(module.tree)
        if isinstance(function, ast.FunctionDef)
        and function.name not in ALLOWED
        and any(isinstance(node, ast.Name) and node.id == GENERIC_REASON for node in ast.walk(function))
    )


def reads_the_error_first(module: SourceModule) -> bool:
    """`_unusable` reads the error of the answer before it falls back on the generic reason."""
    [unusable] = [
        node for node in ast.walk(module.tree) if isinstance(node, ast.FunctionDef) and node.name == "_unusable"
    ]
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == ERROR_READER
        for node in ast.walk(unusable)
    )


def model_call() -> SourceModule:
    [module] = [module for module in source_modules(SOURCE_ROOT) if module.path == MODEL_CALL]
    return module


def test_adr_errore_di_openrouter_nella_risposta_the_generic_reason_comes_after_the_error_of_the_answer() -> None:
    module = model_call()

    assert generic_reasons(module) == []
    assert reads_the_error_first(module)


def test_adr_errore_di_openrouter_nella_risposta_a_generic_reason_from_the_reading_is_a_violation() -> None:
    hiding = SourceModule.parse(
        MODEL_CALL,
        "class OpenRouterModelCallAdapter:\n"
        "    def call(self, document):\n"
        "        raise ModelUnavailableError(OPENROUTER, UNEXPECTED_ANSWER)\n"
        "def _unusable(key, document, usage):\n"
        "    return ModelUnavailableError(OPENROUTER, UNEXPECTED_ANSWER)\n",
    )

    assert generic_reasons(hiding) == ["call"]
    assert not reads_the_error_first(hiding)
