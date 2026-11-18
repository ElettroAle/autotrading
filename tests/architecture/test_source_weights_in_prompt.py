"""ADR-peso-delle-fonti-nel-system-prompt (Bug 622): the model is told what the weight of a source means through the
placeholder `{source_weights}` of the registry, which the default system prompt uses; the code never computes on a
weight, and the limits of the weight have one definition, which the rule reads.
"""

import ast

from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT, PromptPlaceholder
from tests.support.architecture import SourceModule, source_modules

SOURCE_WEIGHTS = "source_weights"
WEIGHT = "weight"
WEIGHT_LIMITS = frozenset({"MINIMUM_WEIGHT", "MAXIMUM_WEIGHT", "DEFAULT_WEIGHT"})
SELECTIONS = "domain/flows/selections.py"
SYSTEM_PROMPT = "domain/flows/system_prompt.py"
AGGREGATIONS = frozenset({"sum", "max", "min", "sorted", "round"})
ARITHMETIC = (ast.BinOp, ast.UnaryOp, ast.AugAssign, ast.BoolOp)

COMPUTING = SourceModule.parse(
    "application/flows/compose_cycle_context.py",
    """
def strongest(sources):
    return max(sources, key=lambda source: source.weight)

def score(signal, source):
    return signal * source.weight

def heavy(source):
    return source.weight > 7
""",
)
REPEATED_LIMIT = SourceModule.parse("domain/agent/agent_context.py", "MAXIMUM_WEIGHT = 10\n")
RULE_WITHOUT_LIMITS = SourceModule.parse(SYSTEM_PROMPT, 'RULE = "il peso è un intero da 1 a 10, predefinito 5"\n')
CONFORMING = (
    SourceModule.parse(
        SELECTIONS,
        """
MINIMUM_WEIGHT = 1
MAXIMUM_WEIGHT = 10
DEFAULT_WEIGHT = 5

def check(self):
    if not MINIMUM_WEIGHT <= self.weight <= MAXIMUM_WEIGHT:
        raise SourceWeightOutOfRangeError(self.name)
""",
    ),
    SourceModule.parse(
        SYSTEM_PROMPT,
        """
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, MAXIMUM_WEIGHT, MINIMUM_WEIGHT

def weights(sources):
    return ", ".join(f"{source.name} {source.weight}" for source in sources)
""",
    ),
)


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def _is_range_check(compare: ast.Compare, weight: ast.AST) -> bool:
    operands = [compare.left, *compare.comparators]
    return all(
        operand is weight or (isinstance(operand, ast.Name) and operand.id in WEIGHT_LIMITS) for operand in operands
    )


def _computes(weight: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    parent = parents.get(weight)
    if isinstance(parent, ARITHMETIC):
        return True
    if isinstance(parent, ast.Compare):
        return not _is_range_check(parent, weight)
    node: ast.AST | None = parent
    while node is not None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in AGGREGATIONS:
            return True
        node = parents.get(node)
    return False


def computations(modules: list[SourceModule]) -> list[str]:
    """Every place where the code computes on the weight of a source instead of telling it to the model."""
    found: list[str] = []
    for module in modules:
        parents = _parents(module.tree)
        lines = sorted(
            node.lineno
            for node in ast.walk(module.tree)
            if isinstance(node, ast.Attribute) and node.attr == WEIGHT and _computes(node, parents)
        )
        found.extend(f"{module.path}:{line}: computes on the weight of a source" for line in lines)
    return found


def _assigned_names(module: SourceModule) -> set[str]:
    return {
        target.id
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def _imported_names(module: SourceModule) -> set[str]:
    return {
        alias.name
        for node in ast.walk(module.tree)
        if isinstance(node, ast.ImportFrom) and node.module == "autotrading.domain.flows.selections"
        for alias in node.names
    }


def limit_violations(modules: list[SourceModule]) -> list[str]:
    """A limit of the weight defined outside the selections, or a rule that does not read the limits from there."""
    found = [
        f"{module.path}: {name} is defined outside {SELECTIONS}"
        for module in modules
        if module.path != SELECTIONS
        for name in sorted(_assigned_names(module) & WEIGHT_LIMITS)
    ]
    found.extend(
        f"{module.path}: the rule of the weights does not read {', '.join(sorted(missing))}"
        for module in modules
        if module.path == SYSTEM_PROMPT
        for missing in (WEIGHT_LIMITS - _imported_names(module),)
        if missing
    )
    return found


def test_adr_peso_delle_fonti_nel_system_prompt_the_default_gives_the_rule_through_its_placeholder() -> None:
    assert SOURCE_WEIGHTS in {placeholder.value for placeholder in PromptPlaceholder}
    assert f"{{{SOURCE_WEIGHTS}}}" in DEFAULT_SYSTEM_PROMPT


def test_adr_peso_delle_fonti_nel_system_prompt_no_code_computes_on_a_weight() -> None:
    assert computations(source_modules()) == []


def test_adr_peso_delle_fonti_nel_system_prompt_the_limits_have_one_definition_read_by_the_rule() -> None:
    assert limit_violations(source_modules()) == []


def test_adr_peso_delle_fonti_nel_system_prompt_a_computation_on_a_weight_is_found() -> None:
    assert computations([COMPUTING]) == [
        "application/flows/compose_cycle_context.py:3: computes on the weight of a source",
        "application/flows/compose_cycle_context.py:6: computes on the weight of a source",
        "application/flows/compose_cycle_context.py:9: computes on the weight of a source",
    ]
    assert computations(list(CONFORMING)) == []


def test_adr_peso_delle_fonti_nel_system_prompt_a_repeated_limit_or_a_rule_with_its_own_numbers_is_found() -> None:
    assert limit_violations([REPEATED_LIMIT, RULE_WITHOUT_LIMITS]) == [
        "domain/agent/agent_context.py: MAXIMUM_WEIGHT is defined outside domain/flows/selections.py",
        f"{SYSTEM_PROMPT}: the rule of the weights does not read DEFAULT_WEIGHT, MAXIMUM_WEIGHT, MINIMUM_WEIGHT",
    ]
    assert limit_violations(list(CONFORMING)) == []
