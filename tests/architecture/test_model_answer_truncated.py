"""ADR-risposta-del-modello-interrotta-dal-limite-di-token: an answer the model cuts at the token limit is a temporary
`ModelAnswerTruncatedError`, which the retry, the cost and the journal treat as every unavailable model. Both adapters
of the model call recognise it from the reason the first choice finished; the error keeps its class and its limit
when it is priced and carries the spend, so the cycle fails with its own reason.
"""

import ast

from autotrading.application.agent.errors import ModelAnswerTruncatedError, ModelUnavailableError
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

MODEL_CALLS = ("adapters/outbound/openrouter/model_call.py", "adapters/outbound/litellm/model_call.py")
ERRORS = "application/agent/errors.py"
TRUNCATED = "ModelAnswerTruncatedError"
UNAVAILABLE = "ModelUnavailableError"
FINISH_REASON = "finish_reason"
COPIES = ("priced", "with_spend")


def model_calls_without_truncation(modules: list[SourceModule]) -> list[str]:
    """The adapters of the model call that never raise the cut answer or never read why the answer finished."""
    return sorted(
        module.path
        for module in modules
        if not (_raises(module.tree, TRUNCATED) and FINISH_REASON in _names_and_texts(module.tree))
    )


def copies_that_drop_the_class(module: SourceModule) -> list[str]:
    """The methods of `ModelUnavailableError` that build a new error of the base class themselves, dropping the class
    and the data of a subclass such as the cut answer.
    """
    [unavailable] = [node for node in module.tree.body if isinstance(node, ast.ClassDef) and node.name == UNAVAILABLE]
    return sorted(
        method.name
        for method in unavailable.body
        if isinstance(method, ast.FunctionDef)
        and method.name in COPIES
        and any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == UNAVAILABLE
            for node in ast.walk(method)
        )
    )


def _raises(tree: ast.Module, name: str) -> bool:
    return any(
        isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, ast.Name)
        and node.exc.func.id == name
        for node in ast.walk(tree)
    )


def _names_and_texts(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def modules_at(paths: tuple[str, ...]) -> list[SourceModule]:
    return [module for module in source_modules(SOURCE_ROOT) if module.path in paths]


def test_adr_risposta_del_modello_interrotta_dal_limite_di_token_a_cut_answer_is_a_temporary_failure() -> None:
    assert issubclass(ModelAnswerTruncatedError, ModelUnavailableError)
    assert not ModelAnswerTruncatedError.declared_permanent
    assert ModelAnswerTruncatedError.status_code == ModelUnavailableError.status_code


def test_adr_risposta_del_modello_interrotta_dal_limite_di_token_both_model_calls_recognise_the_cut_answer() -> None:
    modules = modules_at(MODEL_CALLS)

    assert sorted(module.path for module in modules) == sorted(MODEL_CALLS)
    assert model_calls_without_truncation(modules) == []


def test_adr_risposta_del_modello_interrotta_dal_limite_di_token_the_error_keeps_its_class_through_the_spend() -> None:
    [errors] = modules_at((ERRORS,))

    assert copies_that_drop_the_class(errors) == []


def test_adr_risposta_del_modello_interrotta_dal_limite_di_token_a_hiding_adapter_is_a_violation() -> None:
    hiding = SourceModule.parse(
        "adapters/outbound/litellm/model_call.py",
        "def call(reply):\n    raise ModelUnavailableError(provider, UNEXPECTED_ANSWER, sent=True)\n",
    )
    recognising = SourceModule.parse(
        "adapters/outbound/openrouter/model_call.py",
        "def call(document, first):\n"
        "    if first.get('finish_reason') == 'length':\n"
        "        raise ModelAnswerTruncatedError(OPENROUTER, 4096, sent=True)\n",
    )

    assert model_calls_without_truncation([hiding, recognising]) == ["adapters/outbound/litellm/model_call.py"]


def test_adr_risposta_del_modello_interrotta_dal_limite_di_token_a_copy_of_the_base_class_is_a_violation() -> None:
    dropping = SourceModule.parse(
        ERRORS,
        "class ModelUnavailableError(ApplicationError):\n"
        "    def priced(self, prices):\n"
        "        return ModelUnavailableError(self.provider, self.original)\n"
        "    def with_spend(self, spend):\n"
        "        return self._spent(spend.usage, sent=spend.sent, cost_usd=spend.cost_usd, attempts=spend.attempts)\n",
    )

    assert copies_that_drop_the_class(dropping) == ["priced"]
