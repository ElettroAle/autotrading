"""Every technical decision has one identity, chosen so that parallel pull requests cannot collide on it.

The numbered decisions keep their number; a new decision is named by its title, never by a number picked in a branch
(ADR identita-delle-adr-indipendente-dal-ramo).
"""

import re
from collections import defaultdict
from pathlib import Path

ADR_FOLDER = Path(__file__).resolve().parents[2] / "docs" / "adr"
NUMBERED_NAME = re.compile(r"^(\d{4})-.+\.md$")
TITLED_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
# The last number handed out in a branch, the decisions still open in pull requests when the numbering stopped included.
LAST_NUMBER = 168


def numbered_decisions(folder: Path) -> list[Path]:
    return [adr for adr in folder.iterdir() if NUMBERED_NAME.match(adr.name)]


def titled_decisions(folder: Path) -> list[Path]:
    return [adr for adr in folder.iterdir() if adr.suffix == ".md" and not NUMBERED_NAME.match(adr.name)]


def shared_numbers(folder: Path) -> dict[str, list[str]]:
    files_by_number: dict[str, list[str]] = defaultdict(list)
    for adr in numbered_decisions(folder):
        files_by_number[adr.name[:4]].append(adr.name)
    return {number: sorted(names) for number, names in files_by_number.items() if len(names) > 1}


def numbers_after_the_last(folder: Path) -> list[str]:
    return sorted(adr.name for adr in numbered_decisions(folder) if int(adr.name[:4]) > LAST_NUMBER)


def numbered_headings_without_number(folder: Path) -> list[str]:
    return sorted(
        adr.name
        for adr in numbered_decisions(folder)
        if not adr.read_text(encoding="utf-8").startswith(f"# ADR {adr.name[:4]} ")
    )


def badly_named_titled(folder: Path) -> list[str]:
    return sorted(adr.name for adr in titled_decisions(folder) if not TITLED_NAME.match(adr.name))


def titled_headings_without_name(folder: Path) -> list[str]:
    return sorted(
        adr.name
        for adr in titled_decisions(folder)
        if TITLED_NAME.match(adr.name) and not adr.read_text(encoding="utf-8").startswith(f"# ADR {adr.stem} ")
    )


def test_no_two_decisions_share_a_number() -> None:
    shared = shared_numbers(ADR_FOLDER)

    assert not shared, f"ADR con lo stesso numero, rinumerare la più recente: {shared}"


def test_no_decision_takes_a_new_number() -> None:
    late = numbers_after_the_last(ADR_FOLDER)

    assert not late, f"Una nuova ADR non prende un numero, si chiama docs/adr/<titolo>.md: {late}"


def test_every_numbered_heading_carries_its_file_number() -> None:
    mismatched = numbered_headings_without_number(ADR_FOLDER)

    assert not mismatched, f"Il titolo dell'ADR non riporta il numero del file: {mismatched}"


def test_every_new_decision_is_named_by_its_title() -> None:
    malformed = badly_named_titled(ADR_FOLDER)

    assert not malformed, f"Una nuova ADR si chiama col suo titolo in kebab-case, docs/adr/<titolo>.md: {malformed}"


def test_every_new_decision_heading_carries_its_file_name() -> None:
    mismatched = titled_headings_without_name(ADR_FOLDER)

    assert not mismatched, f"Il titolo di una nuova ADR comincia con '# ADR <nome del file> ': {mismatched}"


def test_a_new_number_is_found(tmp_path: Path) -> None:
    name = f"{LAST_NUMBER + 1:04d}-nuova.md"
    (tmp_path / name).write_text(f"# ADR {LAST_NUMBER + 1:04d} — Nuova\n", encoding="utf-8")

    assert numbers_after_the_last(tmp_path) == [name]


def test_a_numbered_decision_within_the_last_number_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "0001-prima.md").write_text("# ADR 0001 — Prima\n", encoding="utf-8")

    assert numbers_after_the_last(tmp_path) == []
    assert numbered_headings_without_number(tmp_path) == []


def test_a_shared_number_is_found(tmp_path: Path) -> None:
    (tmp_path / "0162-una.md").write_text("# ADR 0162 — Una\n", encoding="utf-8")
    (tmp_path / "0162-altra.md").write_text("# ADR 0162 — Altra\n", encoding="utf-8")

    assert shared_numbers(tmp_path) == {"0162": ["0162-altra.md", "0162-una.md"]}


def test_a_titled_decision_with_its_name_in_the_heading_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "rete-dichiarata.md").write_text("# ADR rete-dichiarata — Rete dichiarata\n", encoding="utf-8")

    assert badly_named_titled(tmp_path) == []
    assert titled_headings_without_name(tmp_path) == []


def test_a_titled_decision_without_its_name_in_the_heading_is_found(tmp_path: Path) -> None:
    (tmp_path / "rete-dichiarata.md").write_text("# Rete dichiarata\n", encoding="utf-8")

    assert titled_headings_without_name(tmp_path) == ["rete-dichiarata.md"]


def test_a_titled_decision_not_in_kebab_case_is_found(tmp_path: Path) -> None:
    (tmp_path / "Rete_Dichiarata.md").write_text("# ADR Rete_Dichiarata — x\n", encoding="utf-8")

    assert badly_named_titled(tmp_path) == ["Rete_Dichiarata.md"]
