"""ADR-stop-che-segue-il-prezzo-nella-dashboard: the parts of the stop that follows the price stay in the section of the
protections right after the default stop loss and take profit, each with what it admits beside it, and the dashboard
repeats none of the rules of the API; the view of the positions shows stop, target and the largest profit reached as
the API gives them.
"""

import re
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src" / "features"
FORM = DASHBOARD / "flow-editor" / "components" / "flow-form.tsx"
FIELDS = DASHBOARD / "flow-editor" / "components" / "trailing-stop-fields.tsx"
FORM_VALUES = DASHBOARD / "flow-editor" / "utils" / "flow-form.ts"
POSITIONS = DASHBOARD / "flow-positions" / "components" / "open-positions.tsx"
FIELD_IDS = ("flow-trailing-distance", "flow-trailing-activation", "flow-trailing-breakeven")
# The bounds and the combination the API checks, written in a form: the dashboard would repeat its rules.
REPEATED_RULE = re.compile(r"trailing_stop[^\n]*\.(refine|min|max)\(|richiede la distanza|va da 0,1 a 50")
# What a part admits, written beside it: a hint of a field or of the list of the parts.
HINT = re.compile(r"\bhint[:=] ?['\"]")


def form_violations(form: str, fields: str, values: str) -> list[str]:
    """What keeps the parts of the stop that follows the price beside the default protections, described, unchecked."""
    found = []
    take_profit, trailing = form.find("register('default_take_profit_percent')"), form.find("<TrailingStopFields />")
    if not 0 <= take_profit < trailing or "<FormField" in form[take_profit:trailing]:
        found.append("the parts are not right after the default take profit")
    found.extend(f"the part {part} is not there" for part in FIELD_IDS if not re.search(f"['\"]{part}['\"]", fields))
    # The shared fields describe their control with their hint (ADR informazioni-sui-campi-di-configurazione).
    described = "aria-describedby" in fields or "<FormField" in fields
    if len(HINT.findall(fields)) < len(FIELD_IDS) or not described:
        found.append("a part without what it admits")
    if REPEATED_RULE.search(fields + values):
        found.append("a rule of the API repeated in the dashboard")
    return found


def positions_violations(positions: str) -> list[str]:
    """What keeps the view of the positions from showing the largest profit reached as the API gives it."""
    headers = re.findall(r"header: '([^']+)'", positions)
    missing = [header for header in ("Obiettivo", "Stop", "Massimo profitto raggiunto") if header not in headers]
    computed = ["the profit computed from prices"] if re.search(r"entry_price\)?\s*[-*]", positions) else []
    return [f"no column {header}" for header in missing] + computed


def test_adr_stop_che_segue_il_prezzo_nella_dashboard_the_parts_follow_the_default_protections() -> None:
    found = form_violations(
        FORM.read_text(encoding="utf-8"),
        FIELDS.read_text(encoding="utf-8"),
        FORM_VALUES.read_text(encoding="utf-8"),
    )

    assert found == []


def test_adr_stop_che_segue_il_prezzo_nella_dashboard_a_separate_section_with_its_own_rules_is_found() -> None:
    form = "<TrailingStopFields />\n<FormField id='flow-default-take-profit'>{register('default_take_profit_percent')}"
    fields = (
        "<fieldset><legend>Stop che segue</legend><input {...register('trailing_stop.distance_percent')} /></fieldset>"
    )
    values = "distance_percent: numberText.refine(within, 'la distanza va da 0,1 a 50'),"

    assert form_violations(form, fields, values) == [
        "the parts are not right after the default take profit",
        "the part flow-trailing-distance is not there",
        "the part flow-trailing-activation is not there",
        "the part flow-trailing-breakeven is not there",
        "a part without what it admits",
        "a rule of the API repeated in the dashboard",
    ]


def test_adr_stop_che_segue_il_prezzo_nella_dashboard_the_positions_show_what_the_api_gives() -> None:
    assert positions_violations(POSITIONS.read_text(encoding="utf-8")) == []


def test_adr_stop_che_segue_il_prezzo_nella_dashboard_a_profit_computed_by_the_view_is_found() -> None:
    view = (
        "{ header: 'Stop', cell: (p) => p.stop_price },\n"
        "{ header: 'Massimo', cell: (p) => (p.mark - p.entry_price) * p.size }"
    )

    assert positions_violations(view) == [
        "no column Obiettivo",
        "no column Massimo profitto raggiunto",
        "the profit computed from prices",
    ]
    assert positions_violations(
        "{ header: 'Obiettivo' }{ header: 'Stop' }{ header: 'Massimo profitto raggiunto', "
        "cell: (p) => (p.mark - p.entry_price) * p.size }"
    ) == ["the profit computed from prices"]
