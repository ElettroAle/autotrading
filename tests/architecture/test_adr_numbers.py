"""Every technical decision has its own number, so a reference to an ADR names exactly one decision."""

import re
from collections import defaultdict
from pathlib import Path

ADR_FOLDER = Path(__file__).resolve().parents[2] / "docs" / "adr"
ADR_NAME = re.compile(r"^(\d{4})-.+\.md$")


def test_no_two_decisions_share_a_number() -> None:
    files_by_number: dict[str, list[str]] = defaultdict(list)
    for adr in ADR_FOLDER.iterdir():
        match = ADR_NAME.match(adr.name)
        if match:
            files_by_number[match.group(1)].append(adr.name)

    shared = {number: sorted(names) for number, names in files_by_number.items() if len(names) > 1}

    assert not shared, f"ADR con lo stesso numero, rinumerare la più recente: {shared}"


def test_every_decision_title_carries_its_file_number() -> None:
    mismatched = [
        adr.name
        for adr in ADR_FOLDER.iterdir()
        if ADR_NAME.match(adr.name) and not adr.read_text(encoding="utf-8").startswith(f"# ADR {adr.name[:4]} ")
    ]

    assert not mismatched, f"Il titolo dell'ADR non riporta il numero del file: {mismatched}"
