"""Static rules on the source tree that keep the layers apart beyond what import-linter can see.

The rules admit no exception by name: the only tolerated violations are the known ones, each with its Bug, listed in
tests/architecture/known_violations.py.
"""

import ast
import builtins
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "autotrading"
MODULE_SCOPE = "<modulo>"


class Rule(StrEnum):
    PORTS_IN_PORTS_MODULES = "porte-solo-in-ports"
    PORT_NAMES = "nomi-delle-porte"
    BOOTSTRAP_WITHOUT_DECISIONS = "bootstrap-senza-decisioni"
    BOOTSTRAP_WITHOUT_CONSTANTS = "bootstrap-senza-costanti"
    BOOTSTRAP_WITHOUT_CLASSES = "bootstrap-senza-classi"
    NO_BRIDGES = "nessun-ponte"
    LIBRARIES_IN_THEIR_FOLDER = "librerie-solo-nella-loro-cartella"
    ADAPTERS_DO_NOT_ORCHESTRATE = "adapter-senza-orchestrazione"
    CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY = "nucleo-senza-librerie-tecniche"
    CORE_WITHOUT_TECHNOLOGY_NAMES = "nucleo-senza-nomi-di-tecnologie"
    ONLY_PROJECT_EXCEPTIONS_RAISED = "solo-eccezioni-del-progetto"
    ERROR_SHAPE = "forma-dell-errore"
    NO_GENERIC_EXCEPT = "nessun-except-generico"
    USE_CASE_SHAPE = "forma-del-caso-d-uso"
    COMMAND_SHAPE = "forma-del-comando"
    ADAPTER_NAMES = "nomi-degli-adapter"
    NO_GENERIC_FOLDERS = "nessuna-cartella-generica"
    NO_ANY = "nessun-any"
    TYPE_IGNORE_EXPLAINED = "type-ignore-motivato"


REMEDIES = {
    Rule.PORTS_IN_PORTS_MODULES: "una porta (Protocol o *Port) vive solo in application/<contesto>/ports.py",
    Rule.PORT_NAMES: "una porta è un typing.Protocol che si chiama <Ruolo>Port",
    Rule.BOOTSTRAP_WITHOUT_DECISIONS: (
        "bootstrap.py istanzia e collega soltanto: la decisione va nel domain o in un caso d'uso, la lettura e la "
        "validazione della configurazione in un adapter, la traduzione nell'adapter della tecnologia"
    ),
    Rule.BOOTSTRAP_WITHOUT_CONSTANTS: (
        "bootstrap.py non dichiara nulla a livello di modulo: la costante va nel domain, il valore di "
        "configurazione nell'adapter che legge la configurazione"
    ),
    Rule.BOOTSTRAP_WITHOUT_CLASSES: (
        "bootstrap.py non definisce classi: la porta va in application/<contesto>/ports.py, la sua realizzazione "
        "in adapters/<verso>/<tecnologia>/, l'orchestrazione in un caso d'uso, l'errore nel livello che lo solleva"
    ),
    Rule.NO_BRIDGES: (
        "non esistono ponti fra contesti: il contesto che usa un dato dichiara la sua porta, l'adapter della "
        "tecnologia che ha il dato la realizza nella sua cartella, il caso d'uso orchestra"
    ),
    Rule.LIBRARIES_IN_THEIR_FOLDER: (
        "un adapter usa una e una sola tecnologia: la libreria si importa solo nella cartella "
        "adapters/<verso>/<tecnologia>/ che la dichiara"
    ),
    Rule.ADAPTERS_DO_NOT_ORCHESTRATE: (
        "un adapter realizza una porta con la sua sola tecnologia: non riceve porte né casi d'uso e da application "
        "importa solo ports.py ed errors.py; l'orchestrazione va nel caso d'uso (unica eccezione: il decorator, che "
        "riceve la stessa porta che dichiara di realizzare)"
    ),
    Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY: (
        "domain, application e bootstrap.py non usano rete, processi, thread o ambiente: la tecnologia va dietro "
        "una porta, in adapters/<verso>/<tecnologia>/"
    ),
    Rule.CORE_WITHOUT_TECHNOLOGY_NAMES: (
        "domain e application non nominano exchange, fornitori, servizi o valute di regolamento: il valore arriva "
        "da una porta o dall'adapter"
    ),
    Rule.ONLY_PROJECT_EXCEPTIONS_RAISED: "si solleva solo un errore che discende da AutotradingError",
    Rule.ERROR_SHAPE: "un errore si chiama <Fatto>Error e discende da un errore del progetto, radice AutotradingError",
    Rule.NO_GENERIC_EXCEPT: "si cattura solo l'eccezione della libreria e la si traduce nell'errore della porta",
    Rule.USE_CASE_SHAPE: (
        "un caso d'uso per modulo, con il solo metodo pubblico execute, nel modulo che porta il suo nome "
        "(RegisterAccountUseCase in register_account.py)"
    ),
    Rule.COMMAND_SHAPE: "un *Command è una dataclass frozen, input del caso d'uso omonimo e nel suo modulo",
    Rule.ADAPTER_NAMES: "una classe pubblica di adapters/outbound si chiama <Tecnologia><Ruolo>Adapter o è un *Error",
    Rule.NO_GENERIC_FOLDERS: "una cartella nomina il suo ruolo o la sua tecnologia, mai common/utils/shared",
    Rule.NO_ANY: "si dichiara il tipo vero: typing.Any non si usa",
    Rule.TYPE_IGNORE_EXPLAINED: (
        "un type: ignore nomina il codice dell'errore e ha un commento col motivo, sulla stessa riga o sopra"
    ),
}

# The external libraries each technology folder may import: one technology per folder, each library in one folder.
TECHNOLOGY_LIBRARIES: dict[str, frozenset[str]] = {
    "adapters/inbound/api": frozenset({"fastapi", "pydantic", "starlette"}),
    "adapters/outbound/httpx": frozenset({"httpx"}),
    # eth_account and requests are the signing and transport libraries of the official Hyperliquid SDK.
    "adapters/outbound/hyperliquid": frozenset({"hyperliquid", "eth_account", "requests"}),
    "adapters/outbound/json": frozenset(),
    "adapters/outbound/libsodium": frozenset({"nacl"}),
    "adapters/outbound/oidc": frozenset({"jwt"}),
    "adapters/outbound/sqlalchemy": frozenset({"sqlalchemy"}),
    "adapters/outbound/threads": frozenset(),
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

STANDARD_LIBRARY = frozenset(sys.stdlib_module_names)
GENERIC_FOLDERS = frozenset({"common", "utils", "util", "shared", "helpers", "misc", "lib"})
PROJECT_ROOT_ERROR = "AutotradingError"
PORTS_MODULE = re.compile(r"application/[a-z_]+/ports\.py")
APPLICATION_CONTRACT_MODULE = re.compile(r"autotrading\.application(\.[a-z_]+)?\.(ports|errors)")
BRIDGE_NAME = re.compile(r"\w*Bridge\w*|\w+From[A-Z]\w*")
TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore(?P<code>\[[^\]]+\])?(?P<rest>.*)")
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
    text: str

    @classmethod
    def parse(cls, path: str, text: str) -> SourceModule:
        return cls(path, ast.parse(text), text)

    @property
    def layer(self) -> str:
        return self.path.split("/")[0]

    @property
    def in_core(self) -> bool:
        return self.layer in {"domain", "application"}

    @property
    def is_bootstrap(self) -> bool:
        return self.path == "bootstrap.py"

    @property
    def technology_folder(self) -> str | None:
        parts = self.path.split("/")
        if parts[0] != "adapters" or len(parts) < 4:
            return None
        return "/".join(parts[:3])

    @property
    def is_outbound_adapter(self) -> bool:
        return self.path.startswith("adapters/outbound/")


@dataclass(frozen=True, slots=True)
class ScopedNode:
    symbol: str
    node: ast.AST


def source_modules(root: Path = SOURCE_ROOT) -> list[SourceModule]:
    return [
        SourceModule.parse(path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("*.py"))
    ]


def technology_folders(root: Path = SOURCE_ROOT) -> list[str]:
    adapters = root / "adapters"
    return sorted(
        folder.relative_to(root).as_posix()
        for direction in adapters.iterdir()
        if direction.is_dir()
        for folder in direction.iterdir()
        if (folder / "__init__.py").is_file()
    )


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


def _violation(rule: Rule, module: SourceModule, scoped: ScopedNode, detail: str, line: int | None = None) -> Violation:
    return Violation(rule, module.path, scoped.symbol, line or _line_of(scoped.node), detail)


def _base_names(node: ast.ClassDef) -> set[str]:
    names = set()
    for base in node.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        if isinstance(target, ast.Name):
            names.add(target.id)
        if isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _classes(module: SourceModule) -> Iterator[tuple[ScopedNode, ast.ClassDef]]:
    for scoped in _scoped_nodes(module):
        if isinstance(scoped.node, ast.ClassDef):
            yield scoped, scoped.node


def _imported_modules(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [node.module]
    return []


def _imports(module: SourceModule) -> Iterator[tuple[ScopedNode, str]]:
    for scoped in _scoped_nodes(module):
        for imported in _imported_modules(scoped.node):
            yield ScopedNode(imported, scoped.node), imported


def _ports_outside_ports_modules(module: SourceModule) -> Iterator[Violation]:
    if PORTS_MODULE.fullmatch(module.path):
        return
    for scoped, node in _classes(module):
        if "Protocol" in _base_names(node) or node.name.endswith("Port"):
            yield _violation(Rule.PORTS_IN_PORTS_MODULES, module, scoped, f"porta {node.name} definita qui")


def _port_names(module: SourceModule) -> Iterator[Violation]:
    in_ports_module = bool(PORTS_MODULE.fullmatch(module.path))
    for scoped, node in _classes(module):
        is_protocol = "Protocol" in _base_names(node)
        if in_ports_module and is_protocol and not node.name.endswith("Port"):
            yield _violation(Rule.PORT_NAMES, module, scoped, f"Protocol {node.name} senza il suffisso Port")
        if node.name.endswith("Port") and not is_protocol:
            yield _violation(Rule.PORT_NAMES, module, scoped, f"{node.name} non è un Protocol")


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
    if not module.is_bootstrap:
        return
    for scoped in _scoped_nodes(module, skip_annotations=True):
        if _is_decision(scoped.node):
            detail = f"{type(scoped.node).__name__} in {scoped.symbol}"
            yield _violation(Rule.BOOTSTRAP_WITHOUT_DECISIONS, module, scoped, detail)


def _assigned_names(node: ast.stmt) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    return [target.id for target in targets if isinstance(target, ast.Name)]


def _constants_in_bootstrap(module: SourceModule) -> Iterator[Violation]:
    if not module.is_bootstrap:
        return
    for statement in module.tree.body:
        for name in _assigned_names(statement):
            yield _violation(Rule.BOOTSTRAP_WITHOUT_CONSTANTS, module, ScopedNode(name, statement), f"costante {name}")


def _classes_in_bootstrap(module: SourceModule) -> Iterator[Violation]:
    if not module.is_bootstrap:
        return
    for node in module.tree.body:
        if isinstance(node, ast.ClassDef):
            yield _violation(Rule.BOOTSTRAP_WITHOUT_CLASSES, module, ScopedNode(node.name, node), f"classe {node.name}")


def _bridges(module: SourceModule) -> Iterator[Violation]:
    for scoped, node in _classes(module):
        if BRIDGE_NAME.fullmatch(node.name):
            yield _violation(Rule.NO_BRIDGES, module, scoped, f"classe ponte {node.name}")


def _libraries_outside_their_folder(module: SourceModule) -> Iterator[Violation]:
    folder = module.technology_folder
    allowed = TECHNOLOGY_LIBRARIES.get(folder, frozenset()) if folder else frozenset()
    place = folder or module.path
    for scoped, imported in _imports(module):
        library = imported.split(".")[0]
        if library in STANDARD_LIBRARY or library == "autotrading" or library in allowed:
            continue
        yield _violation(Rule.LIBRARIES_IN_THEIR_FOLDER, module, scoped, f"libreria {library} in {place}")


def _annotation_names(annotation: ast.expr | None) -> set[str]:
    if annotation is None:
        return set()
    names = set()
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name):
            names.add(node.id)
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.update(re.findall(r"\w+", node.value))
    return names


def _collaborators(initializer: ast.FunctionDef) -> list[str]:
    arguments = [*initializer.args.posonlyargs, *initializer.args.args, *initializer.args.kwonlyargs]
    return sorted(
        name
        for argument in arguments
        for name in _annotation_names(argument.annotation)
        if name.endswith(("Port", "UseCase"))
    )


def _is_decorator(node: ast.ClassDef, collaborators: list[str]) -> bool:
    return len(collaborators) == 1 and collaborators[0].endswith("Port") and collaborators[0] in _base_names(node)


def _orchestrating_adapters(module: SourceModule) -> Iterator[Violation]:
    if not module.is_outbound_adapter:
        return
    for scoped, imported in _imports(module):
        if imported.startswith("autotrading.application") and not APPLICATION_CONTRACT_MODULE.fullmatch(imported):
            yield _violation(Rule.ADAPTERS_DO_NOT_ORCHESTRATE, module, scoped, f"import di {imported}")
    for scoped, node in _classes(module):
        initializers = [m for m in node.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"]
        for initializer in initializers:
            collaborators = _collaborators(initializer)
            if collaborators and not _is_decorator(node, collaborators):
                detail = f"{node.name} riceve {', '.join(collaborators)}"
                yield _violation(Rule.ADAPTERS_DO_NOT_ORCHESTRATE, module, scoped, detail, initializer.lineno)


def _technical_standard_library_in_core(module: SourceModule) -> Iterator[Violation]:
    if not (module.in_core or module.is_bootstrap):
        return
    for scoped, imported in _imports(module):
        if imported.split(".")[0] in TECHNICAL_STANDARD_LIBRARY:
            yield _violation(Rule.CORE_WITHOUT_TECHNICAL_STANDARD_LIBRARY, module, scoped, f"import di {imported}")


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


def _error_shapes(module: SourceModule) -> Iterator[Violation]:
    for scoped, node in _classes(module):
        if node.name == PROJECT_ROOT_ERROR:
            continue
        bases = _base_names(node)
        system_bases = sorted(bases & SYSTEM_EXCEPTIONS)
        if system_bases:
            yield _violation(Rule.ERROR_SHAPE, module, scoped, f"{node.name} discende da {', '.join(system_bases)}")
            continue
        if node.name.endswith("Error") and not any(base.endswith("Error") for base in bases):
            yield _violation(Rule.ERROR_SHAPE, module, scoped, f"{node.name} non discende da un errore")


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


def _module_name_of(type_name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", type_name).lower() + ".py"


def _use_case_shapes(module: SourceModule) -> Iterator[Violation]:
    if module.layer != "application":
        return
    use_cases = [node for node in module.tree.body if isinstance(node, ast.ClassDef) and node.name.endswith("UseCase")]
    for node in use_cases[1:]:
        yield _violation(Rule.USE_CASE_SHAPE, module, ScopedNode(node.name, node), f"secondo caso d'uso {node.name}")
    module_name = module.path.rsplit("/", maxsplit=1)[-1]
    for node in use_cases:
        scoped = ScopedNode(node.name, node)
        methods = _public_methods(node)
        if methods != ["execute"]:
            yield _violation(Rule.USE_CASE_SHAPE, module, scoped, f"metodi pubblici {methods}")
        expected = _module_name_of(node.name.removesuffix("UseCase"))
        if module_name != expected:
            yield _violation(Rule.USE_CASE_SHAPE, module, scoped, f"{node.name} in {module_name}, atteso {expected}")


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
    top_level = {node.name for node in module.tree.body if isinstance(node, ast.ClassDef)}
    for scoped, node in _classes(module):
        if not node.name.endswith("Command"):
            continue
        if not any(_is_frozen_dataclass(decorator) for decorator in node.decorator_list):
            yield _violation(Rule.COMMAND_SHAPE, module, scoped, f"{node.name} non è una dataclass frozen")
        use_case = node.name.removesuffix("Command") + "UseCase"
        if use_case not in top_level:
            yield _violation(Rule.COMMAND_SHAPE, module, scoped, f"{node.name} senza {use_case} nel suo modulo")


def _adapter_names(module: SourceModule) -> Iterator[Violation]:
    if not module.is_outbound_adapter:
        return
    for node in module.tree.body:
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        if not node.name.endswith(("Adapter", "Error")):
            yield _violation(Rule.ADAPTER_NAMES, module, ScopedNode(node.name, node), f"classe pubblica {node.name}")


def _generic_folders(module: SourceModule) -> Iterator[Violation]:
    for folder in module.path.split("/")[:-1]:
        if folder in GENERIC_FOLDERS:
            yield _violation(Rule.NO_GENERIC_FOLDERS, module, ScopedNode(folder, module.tree), f"cartella {folder}", 1)


def _any_uses(module: SourceModule) -> Iterator[Violation]:
    for scoped in _scoped_nodes(module):
        node = scoped.node
        imports_any = isinstance(node, ast.ImportFrom) and any(alias.name == "Any" for alias in node.names)
        reads_any = isinstance(node, ast.Attribute) and node.attr == "Any"
        if imports_any or reads_any:
            yield _violation(Rule.NO_ANY, module, ScopedNode("typing.Any", node), "typing.Any")


def _unexplained_type_ignores(module: SourceModule) -> Iterator[Violation]:
    lines = module.text.splitlines()
    for number, line in enumerate(lines, start=1):
        found = TYPE_IGNORE.search(line)
        if not found:
            continue
        above = lines[number - 2].strip() if number > 1 else ""
        explained = found["rest"].strip().startswith("#") or above.startswith("#")
        if found["code"] and explained:
            continue
        scoped = ScopedNode(f"riga {number}", module.tree)
        yield _violation(Rule.TYPE_IGNORE_EXPLAINED, module, scoped, line.strip(), number)


CHECKS: tuple[Callable[[SourceModule], Iterator[Violation]], ...] = (
    _ports_outside_ports_modules,
    _port_names,
    _decisions_in_bootstrap,
    _constants_in_bootstrap,
    _classes_in_bootstrap,
    _bridges,
    _libraries_outside_their_folder,
    _orchestrating_adapters,
    _technical_standard_library_in_core,
    _technology_names_in_core,
    _system_exceptions_raised,
    _error_shapes,
    _generic_excepts,
    _use_case_shapes,
    _command_shapes,
    _adapter_names,
    _generic_folders,
    _any_uses,
    _unexplained_type_ignores,
)
