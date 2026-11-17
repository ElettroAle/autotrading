"""ADR-eccezioni-delle-vulnerabilita-npm-con-scadenza: an advisory without a fix is accepted with reason and expiry.

The vulnerability check of the dashboard runs better-npm-audit at level low: every vulnerability blocks, except one
listed in dashboard/.nsprc with notes that say when it was added and why, and an expiry at most 14 days after that day.
At the expiry the check turns red again and the exception needs an explicit choice.
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
EXCEPTIONS = REPOSITORY / "dashboard" / ".nsprc"
ACTION = REPOSITORY / ".github" / "actions" / "npm-audit" / "action.yml"
PACKAGE = REPOSITORY / "dashboard" / "package.json"
LIBRARY = "better-npm-audit"
AUDIT = "better-npm-audit audit --level low"
POLICY_FLAGS = ("--require-notes", "--require-expiry", "--max-expiry-days 14")
MAXIMUM_DURATION = timedelta(days=14)
ADDED = re.compile(r"^Aggiunta il (?P<day>\d{4}-\d{2}-\d{2})\. \S")
EXPIRY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

type ExceptionEntry = dict[str, object]


def _added_on(notes: object) -> date | None:
    match = ADDED.match(notes) if isinstance(notes, str) else None
    return date.fromisoformat(match["day"]) if match else None


def _expires_on(expiry: object) -> date | None:
    return date.fromisoformat(expiry) if isinstance(expiry, str) and EXPIRY.match(expiry) else None


def exception_violations(advisory: str, exception: ExceptionEntry) -> list[str]:
    """The broken rules of one exception of .nsprc."""
    added = _added_on(exception.get("notes"))
    if added is None:
        return [f"{advisory}: le note iniziano con «Aggiunta il AAAA-MM-GG.» e dicono il motivo"]
    expires = _expires_on(exception.get("expiry"))
    if expires is None:
        return [f"{advisory}: la scadenza è una data AAAA-MM-GG"]
    if not added < expires <= added + MAXIMUM_DURATION:
        return [f"{advisory}: la scadenza cade al più 14 giorni dopo il {added.isoformat()}"]
    return []


def exceptions_violations(content: str) -> list[str]:
    exceptions = json.loads(content)
    found: list[str] = []
    for advisory, exception in exceptions.items():
        if not isinstance(exception, dict):
            found.append(f"{advisory}: l'eccezione ha note e scadenza, non solo un testo")
            continue
        found.extend(exception_violations(advisory, exception))
    return found


def action_violations(action: str) -> list[str]:
    """The broken rules of the npm-audit action."""
    found = []
    if AUDIT not in action:
        found.append(f"l'azione npm-audit esegue «{AUDIT}»")
    found.extend(f"l'azione npm-audit impone {flag}" for flag in POLICY_FLAGS if flag not in action)
    return found


CONFORMING_EXCEPTION: ExceptionEntry = {
    "active": True,
    "notes": "Aggiunta il 2026-11-17. Nessuna correzione, solo strumenti di sviluppo.",
    "expiry": "2026-12-01",
}
VIOLATING_EXCEPTIONS: list[ExceptionEntry] = [
    {**CONFORMING_EXCEPTION, "notes": ""},
    {**CONFORMING_EXCEPTION, "notes": "Nessuna correzione, solo strumenti di sviluppo."},
    {**CONFORMING_EXCEPTION, "notes": "Aggiunta il 2026-11-17."},
    {key: value for key, value in CONFORMING_EXCEPTION.items() if key != "expiry"},
    {**CONFORMING_EXCEPTION, "expiry": 1796083200},
    {**CONFORMING_EXCEPTION, "expiry": "2026-12-02"},
    {**CONFORMING_EXCEPTION, "expiry": "2026-11-17"},
]
CONFORMING_ACTION = f"run: npx --no-install {AUDIT} {' '.join(POLICY_FLAGS)}\n"
VIOLATING_ACTIONS = [
    "run: npm audit --audit-level=low\n",
    CONFORMING_ACTION.replace("--level low", "--level high"),
    *(CONFORMING_ACTION.replace(f" {flag}", "") for flag in POLICY_FLAGS),
]


@pytest.mark.parametrize("exception", VIOLATING_EXCEPTIONS)
def test_each_exception_rule_catches_its_violation(exception: ExceptionEntry) -> None:
    assert exception_violations("GHSA-0000-0000-0000", exception)


def test_a_conforming_exception_breaks_no_rule() -> None:
    assert exception_violations("GHSA-0000-0000-0000", CONFORMING_EXCEPTION) == []


def test_an_exception_without_details_is_a_violation() -> None:
    assert exceptions_violations('{"GHSA-0000-0000-0000": "solo un testo"}')


@pytest.mark.parametrize("action", VIOLATING_ACTIONS)
def test_each_action_rule_catches_its_violation(action: str) -> None:
    assert action_violations(action)


def test_a_conforming_action_breaks_no_rule() -> None:
    assert action_violations(CONFORMING_ACTION) == []


def test_every_exception_of_the_dashboard_has_a_reason_and_a_near_expiry() -> None:
    assert exceptions_violations(EXCEPTIONS.read_text(encoding="utf-8")) == []


def test_the_vulnerability_check_runs_the_library_with_the_exception_policy() -> None:
    assert action_violations(ACTION.read_text(encoding="utf-8")) == []


def test_the_library_is_a_pinned_development_dependency_of_the_dashboard() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))

    assert re.fullmatch(r"\d+\.\d+\.\d+", package["devDependencies"].get(LIBRARY, ""))
