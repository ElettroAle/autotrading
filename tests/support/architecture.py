"""Static rules on the source tree that keep the layers apart beyond what import-linter can see."""

import ast
import builtins
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "autotrading"
MODULE_SCOPE = "<modulo>"


class Rule(StrEnum):
    PORTS_IN_PORTS_MODULES = "porte-solo-in-ports"
    BOOTSTRAP_WITHOUT_DECISIONS = "bootstrap-senza-decisioni"
    BOOTSTRAP_WITHOUT_BUSINESS_CONSTANTS = "bootstrap-senza-costanti-di-business"
    CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY = "nucleo-senza-librerie-tecniche"
    CORE_WITHOUT_TECHNOLOGY_NAMES = "nucleo-senza-nomi-di-tecnologie"
    ONLY_PROJECT_EXCEPTIONS_RAISED = "solo-eccezioni-del-progetto"
    NO_GENERIC_EXCEPT = "nessun-except-generico"
    USE_CASE_SHAPE = "forma-del-caso-d-uso"
    COMMAND_SHAPE = "forma-del-comando"
    ADAPTER_NAMES = "nomi-degli-adapter"


REMEDIES = {
    Rule.PORTS_IN_PORTS_MODULES: "una porta (Protocol o *Port) vive solo in application/<contesto>/ports.py",
    Rule.BOOTSTRAP_WITHOUT_DECISIONS: (
        "bootstrap.py collega soltanto: la decisione va nel domain o in un caso d'uso, la traduzione nell'adapter"
    ),
    Rule.BOOTSTRAP_WITHOUT_BUSINESS_CONSTANTS: (
        "bootstrap.py dichiara solo nomi e valori di configurazione: la costante va nel domain o nell'adapter"
    ),
    Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY: (
        "domain e application non usano rete, processi, thread o ambiente: la tecnologia va dietro una porta, "
        "in adapters/outbound/<tecnologia>/"
    ),
    Rule.CORE_WITHOUT_TECHNOLOGY_NAMES: (
        "domain e application non nominano exchange, fornitori, servizi o valute di regolamento: il valore arriva "
        "da una porta o dall'adapter"
    ),
    Rule.ONLY_PROJECT_EXCEPTIONS_RAISED: "si solleva solo un errore che discende da AutotradingError",
    Rule.NO_GENERIC_EXCEPT: "si cattura solo l'eccezione della libreria e la si traduce nell'errore della porta",
    Rule.USE_CASE_SHAPE: "un caso d'uso per modulo, con il solo metodo pubblico execute",
    Rule.COMMAND_SHAPE: "un *Command è una dataclass frozen, input di un caso d'uso",
    Rule.ADAPTER_NAMES: "una classe pubblica di adapters/outbound si chiama <Tecnologia><Ruolo>Adapter o è un *Error",
}

# Reading a setting and refusing it at startup is composition, not business: these functions may branch.
CONFIGURATION_READERS = {
    "_required": "rifiuta all'avvio un'impostazione obbligatoria assente",
    "_secret": "legge un segreto da un file montato e lo rifiuta se vuoto (ADR 0015)",
    "_optional_secret": "un segreto che l'installazione può non avere ancora",
    "_environment": "rifiuta all'avvio un ambiente non dichiarato o non ammesso",
    "_authentication": "senza identity provider dichiarato le funzioni protette rispondono 503 (ADR 0016)",
    "_credentials_public_key": "rifiuta all'avvio una chiave pubblica malformata",
    "_credentials_private_key": "rifiuta all'avvio una chiave privata malformata",
    "slippage_from": "legge lo slippage dell'installazione, con il default del dominio se assente",
}

# The only module-level names bootstrap.py may declare: names and values of the configuration.
CONFIGURATION_CONSTANTS = {
    "SUPPORTED_ENVIRONMENTS": "ambienti ammessi dall'installazione",
    "DEFAULT_DATABASE_PORT": "porta del database se l'installazione non la dichiara",
    "DEFAULT_CREDENTIALS_KEY_VERSION": "versione della chiave delle credenziali se non dichiarata",
    "HYPERLIQUID": "nome con cui un conto indica l'exchange: sceglie l'adapter",
    "SLIPPAGE_SETTING": "nome dell'impostazione dello slippage",
    "SOURCE_CATALOG": "fonti che l'installazione collega agli adapter",
    "MODEL_CATALOG": "catalogo dei modelli letto dal suo adapter",
    "PROVIDER_TIMEOUT_SECONDS": "attesa massima verso i fornitori IA",
    "TELEGRAM_BOT_SETTING": "nome dell'impostazione del file del token del bot",
    "WORKER_TIMEOUT_SECONDS": "attesa massima verso il worker",
    "operations": "logger delle operazioni",
}

TECHNICAL_STANDARD_LIBRARY = frozenset(
    {
        "asyncio",
        "concurrent",
        "ftplib",
        "http",
        "multiprocessing",
        "os",
        "selectors",
        "smtplib",
        "socket",
        "sqlite3",
        "ssl",
        "subprocess",
        "threading",
        "urllib",
    }
)

TECHNOLOGY_NAMES = (
    "hyperliquid",
    "telegram",
    "t.me",
    "postgres",
    "sql",
    "http://",
    "https://",
    "anthropic",
    "openai",
    "deepseek",
    "openrouter",
    "usdc",
    "litellm",
)

SYSTEM_EXCEPTIONS = frozenset(
    name
    for name in dir(builtins)
    if isinstance(getattr(builtins, name), type) and issubclass(getattr(builtins, name), BaseException)
)

DECISIONS = (
    ast.If,
    ast.IfExp,
    ast.Match,
    ast.BoolOp,
    ast.Compare,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.TryStar,
    ast.AugAssign,
)

PORTS_MODULE = re.compile(r"application/[a-z_]+/ports\.py")
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
ANNOTATION_FIELDS = frozenset({"annotation", "returns"})


@dataclass(frozen=True, slots=True)
class Violation:
    rule: Rule
    path: str
    symbol: str
    line: int
    detail: str

    @property
    def location(self) -> str:
        return f"{self.path}:{self.symbol}"

    def describe(self) -> str:
        return f"src/autotrading/{self.path}:{self.line} [{self.rule}] {self.detail} -> {REMEDIES[self.rule]}"


@dataclass(frozen=True, slots=True)
class SourceModule:
    path: str
    tree: ast.Module

    @classmethod
    def parse(cls, path: str, text: str) -> SourceModule:
        return cls(path, ast.parse(text))

    @property
    def layer(self) -> str:
        return self.path.split("/")[0]

    @property
    def in_core(self) -> bool:
        return self.layer in {"domain", "application"}


@dataclass(frozen=True, slots=True)
class ScopedNode:
    symbol: str
    node: ast.AST


def source_modules(root: Path = SOURCE_ROOT) -> list[SourceModule]:
    return [
        SourceModule.parse(path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("*.py"))
    ]


def violations_of(module: SourceModule) -> list[Violation]:
    return [violation for check in CHECKS for violation in check(module)]


def _scoped_nodes(module: SourceModule, *, skip_annotations: bool = False) -> Iterator[ScopedNode]:
    yield from _walk(module.tree, (), skip_annotations=skip_annotations)


def _walk(node: ast.AST, scope: tuple[str, ...], *, skip_annotations: bool) -> Iterator[ScopedNode]:
    for field, value in ast.iter_fields(node):
        if skip_annotations and (field in ANNOTATION_FIELDS or isinstance(node, ast.TypeAlias)):
            continue
        for child in value if isinstance(value, list) else [value]:
            if not isinstance(child, ast.AST):
                continue
            inner = (*scope, child.name) if isinstance(child, SCOPES) else scope
            yield ScopedNode(".".join(inner) or MODULE_SCOPE, child)
            yield from _walk(child, inner, skip_annotations=skip_annotations)


def _line_of(node: ast.AST) -> int:
    if isinstance(node, ast.comprehension):
        return node.iter.lineno
    return getattr(node, "lineno", 0)


def _violation(rule: Rule, module: SourceModule, scoped: ScopedNode, detail: str) -> Violation:
    return Violation(rule, module.path, scoped.symbol, _line_of(scoped.node), detail)


def _top_level_symbol(symbol: str) -> str:
    return symbol.split(".", maxsplit=1)[0]


def _base_names(node: ast.ClassDef) -> set[str]:
    names = set()
    for base in node.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        if isinstance(target, ast.Name):
            names.add(target.id)
        if isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _ports_outside_ports_modules(module: SourceModule) -> Iterator[Violation]:
    if PORTS_MODULE.fullmatch(module.path):
        return
    for scoped in _scoped_nodes(module):
        node = scoped.node
        if not isinstance(node, ast.ClassDef):
            continue
        if "Protocol" in _base_names(node) or node.name.endswith("Port"):
            yield _violation(Rule.PORTS_IN_PORTS_MODULES, module, scoped, f"porta {node.name} definita qui")


def _is_text_concatenation(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Add)
        and any(
            isinstance(side, ast.JoinedStr) or (isinstance(side, ast.Constant) and isinstance(side.value, str))
            for side in (node.left, node.right)
        )
    )


def _is_decision(node: ast.AST) -> bool:
    if isinstance(node, ast.comprehension):
        return bool(node.ifs)
    if isinstance(node, ast.BinOp):
        return not _is_text_concatenation(node)
    return isinstance(node, DECISIONS)


def _decisions_in_bootstrap(module: SourceModule) -> Iterator[Violation]:
    if module.path != "bootstrap.py":
        return
    for scoped in _scoped_nodes(module, skip_annotations=True):
        if _top_level_symbol(scoped.symbol) in CONFIGURATION_READERS or not _is_decision(scoped.node):
            continue
        detail = f"{type(scoped.node).__name__} in {scoped.symbol}"
        yield _violation(Rule.BOOTSTRAP_WITHOUT_DECISIONS, module, scoped, detail)


def _assigned_names(node: ast.stmt) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    return [target.id for target in targets if isinstance(target, ast.Name)]


def _business_constants_in_bootstrap(module: SourceModule) -> Iterator[Violation]:
    if module.path != "bootstrap.py":
        return
    for statement in module.tree.body:
        for name in _assigned_names(statement):
            if name in CONFIGURATION_CONSTANTS:
                continue
            scoped = ScopedNode(name, statement)
            yield _violation(Rule.BOOTSTRAP_WITHOUT_BUSINESS_CONSTANTS, module, scoped, f"costante {name}")


def _imported_modules(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [node.module]
    return []


def _technical_standard_library_in_core(module: SourceModule) -> Iterator[Violation]:
    if not module.in_core:
        return
    for scoped in _scoped_nodes(module):
        for imported in _imported_modules(scoped.node):
            if imported.split(".")[0] not in TECHNICAL_STANDARD_LIBRARY:
                continue
            scoped_module = ScopedNode(imported, scoped.node)
            yield _violation(
                Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, module, scoped_module, f"import di {imported}"
            )


def _docstrings(module: SourceModule) -> set[int]:
    owners = [module.tree, *(node for node in ast.walk(module.tree) if isinstance(node, SCOPES))]
    return {
        id(owner.body[0].value)
        for owner in owners
        if owner.body
        and isinstance(owner.body[0], ast.Expr)
        and isinstance(owner.body[0].value, ast.Constant)
        and isinstance(owner.body[0].value.value, str)
    }


def _technology_names_in_core(module: SourceModule) -> Iterator[Violation]:
    if not module.in_core:
        return
    docstrings = _docstrings(module)
    for scoped in _scoped_nodes(module):
        node = scoped.node
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or id(node) in docstrings:
            continue
        names = [name for name in TECHNOLOGY_NAMES if name in node.value.lower()]
        if names:
            detail = f"{', '.join(names)} nel testo {node.value!r}"
            yield _violation(Rule.CORE_WITHOUT_TECHNOLOGY_NAMES, module, scoped, detail)


def _raised_name(node: ast.Raise) -> str | None:
    raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
    return raised.id if isinstance(raised, ast.Name) else None


def _system_exceptions_raised(module: SourceModule) -> Iterator[Violation]:
    for scoped in _scoped_nodes(module):
        if not isinstance(scoped.node, ast.Raise):
            continue
        name = _raised_name(scoped.node)
        if name in SYSTEM_EXCEPTIONS:
            yield _violation(Rule.ONLY_PROJECT_EXCEPTIONS_RAISED, module, scoped, f"raise {name}")


def _caught_names(node: ast.ExceptHandler) -> list[str]:
    if node.type is None:
        return ["<tutto>"]
    caught = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
    return [ast.unparse(name) for name in caught]


def _generic_excepts(module: SourceModule) -> Iterator[Violation]:
    for scoped in _scoped_nodes(module):
        if not isinstance(scoped.node, ast.ExceptHandler):
            continue
        generic = [name for name in _caught_names(scoped.node) if name in {"<tutto>", "Exception", "BaseException"}]
        if generic:
            yield _violation(Rule.NO_GENERIC_EXCEPT, module, scoped, f"except {', '.join(generic)}")


def _public_methods(node: ast.ClassDef) -> list[str]:
    return [
        member.name
        for member in node.body
        if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef) and not member.name.startswith("_")
    ]


def _use_case_shapes(module: SourceModule) -> Iterator[Violation]:
    if module.layer != "application":
        return
    use_cases = [node for node in module.tree.body if isinstance(node, ast.ClassDef) and node.name.endswith("UseCase")]
    for node in use_cases[1:]:
        scoped = ScopedNode(node.name, node)
        yield _violation(Rule.USE_CASE_SHAPE, module, scoped, f"secondo caso d'uso {node.name} nel modulo")
    for node in use_cases:
        methods = _public_methods(node)
        if methods != ["execute"]:
            yield _violation(Rule.USE_CASE_SHAPE, module, ScopedNode(node.name, node), f"metodi pubblici {methods}")


def _is_frozen_dataclass(decorator: ast.expr) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and ast.unparse(decorator.func).split(".")[-1] == "dataclass"
        and any(
            keyword.arg == "frozen" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
            for keyword in decorator.keywords
        )
    )


def _command_shapes(module: SourceModule) -> Iterator[Violation]:
    for scoped in _scoped_nodes(module):
        node = scoped.node
        if not isinstance(node, ast.ClassDef) or not node.name.endswith("Command"):
            continue
        if not any(_is_frozen_dataclass(decorator) for decorator in node.decorator_list):
            yield _violation(Rule.COMMAND_SHAPE, module, scoped, f"{node.name} non è una dataclass frozen")


def _adapter_names(module: SourceModule) -> Iterator[Violation]:
    if not module.path.startswith("adapters/outbound/"):
        return
    for node in module.tree.body:
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        if not node.name.endswith(("Adapter", "Error")):
            scoped = ScopedNode(node.name, node)
            yield _violation(Rule.ADAPTER_NAMES, module, scoped, f"classe pubblica {node.name}")


CHECKS: tuple[Callable[[SourceModule], Iterator[Violation]], ...] = (
    _ports_outside_ports_modules,
    _decisions_in_bootstrap,
    _business_constants_in_bootstrap,
    _technical_standard_library_in_core,
    _technology_names_in_core,
    _system_exceptions_raised,
    _generic_excepts,
    _use_case_shapes,
    _command_shapes,
    _adapter_names,
)
