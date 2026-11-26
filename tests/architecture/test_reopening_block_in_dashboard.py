"""ADR-blocco-delle-riaperture-nella-dashboard: the parts of the block of the reopenings stay in the section of the risk
limits right after the maximum losses and their resume, each with what it admits beside it, and the dashboard repeats
none of the rules of the API; the page of the flow shows the blocks in force beside the suspension of the openings, with
the text the API gives.
"""

import re
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src"
FEATURES = DASHBOARD / "features"
FORM = FEATURES / "flow-editor" / "components" / "flow-form.tsx"
FIELDS = FEATURES / "flow-editor" / "components" / "consecutive-loss-fields.tsx"
FORM_VALUES = FEATURES / "flow-editor" / "utils" / "flow-form.ts"
FLOW_PAGE = DASHBOARD / "app" / "routes" / "app" / "flow.tsx"
BLOCKS = FEATURES / "flow-commands" / "components" / "reopening-blocks.tsx"
BLOCKS_READING = FEATURES / "flow-commands" / "api" / "get-openings-suspension.ts"
FIELD_IDS = ("flow-loss-limit-losses", "flow-loss-limit-window", "flow-loss-limit-block", "flow-loss-limit-scope")
# The bounds and the combination the API checks, written in a form: the dashboard would repeat its rules.
REPEATED_RULE = re.compile(
    r"consecutive_loss_limit[^\n]*\.(refine|min|max|superRefine)\(|almeno 1|si impostano insieme|asset oppure flusso"
)
HINT = re.compile(r"\bhint[:=] ?['\"]")
# The text of a block composed by the dashboard, instead of the one the API gives.
COMPOSED_TEXT = re.compile(r"ferme fino alle|perdit[ae] consecutiv")


def form_violations(form: str, fields: str, values: str) -> list[str]:
    """What keeps the parts of the block beside the maximum losses, described, unchecked."""
    found = []
    resume, limit = form.find("register('openings_resume')"), form.find("<ConsecutiveLossFields />")
    if not 0 <= resume < limit or "<FormField" in form[resume:limit] or "<InputField" in form[resume:limit]:
        found.append("the parts are not right after the resume of the openings")
    found.extend(f"the part {part} is not there" for part in FIELD_IDS if not re.search(f"['\"]{part}['\"]", fields))
    if len(HINT.findall(fields)) < len(FIELD_IDS):
        found.append("a part without what it admits")
    if REPEATED_RULE.search(fields + values):
        found.append("a rule of the API repeated in the dashboard")
    return found


def page_violations(page: str, blocks: str, reading: str) -> list[str]:
    """What keeps the page of the flow from showing the blocks beside the suspension, with the text of the API."""
    found = []
    suspension, shown = page.find("<OpeningsSuspension "), page.find("<ReopeningBlocks ")
    if not 0 <= suspension < shown or "<FlowCommands" in page[suspension:shown]:
        found.append("the blocks are not beside the suspension of the openings")
    if "block.text" not in reading or COMPOSED_TEXT.search(blocks + reading):
        found.append("a text of a block composed by the dashboard")
    return found


def test_adr_blocco_delle_riaperture_nella_dashboard_the_parts_follow_the_maximum_losses() -> None:
    found = form_violations(
        FORM.read_text(encoding="utf-8"),
        FIELDS.read_text(encoding="utf-8"),
        FORM_VALUES.read_text(encoding="utf-8"),
    )

    assert found == []


def test_adr_blocco_delle_riaperture_nella_dashboard_a_separate_section_with_its_own_rules_is_found() -> None:
    form = "<ConsecutiveLossFields />\n<SelectField id='flow-openings-resume' {...register('openings_resume')} />"
    fields = "<input {...register('consecutive_loss_limit.max_consecutive_losses')} />"
    values = "max_consecutive_losses: numberText.refine(atLeastOne, 'le perdite consecutive massime sono almeno 1'),"

    assert form_violations(form, fields, values) == [
        "the parts are not right after the resume of the openings",
        "the part flow-loss-limit-losses is not there",
        "the part flow-loss-limit-window is not there",
        "the part flow-loss-limit-block is not there",
        "the part flow-loss-limit-scope is not there",
        "a part without what it admits",
        "a rule of the API repeated in the dashboard",
    ]


def test_adr_blocco_delle_riaperture_nella_dashboard_the_page_shows_the_blocks_as_the_api_gives_them() -> None:
    found = page_violations(
        FLOW_PAGE.read_text(encoding="utf-8"),
        BLOCKS.read_text(encoding="utf-8"),
        BLOCKS_READING.read_text(encoding="utf-8"),
    )

    assert found == []


def test_adr_blocco_delle_riaperture_nella_dashboard_blocks_apart_with_a_composed_text_are_found() -> None:
    page = "<ReopeningBlocks flowId={flow.id} />\n<FlowCommands />\n<OpeningsSuspension flowId={flow.id} />"
    blocks = "{blocks.map((block) => <p>{`riaperture ${block.side} ferme fino alle ${block.until}`}</p>)}"

    assert page_violations(page, blocks, "select: (state) => state.reopening_blocks") == [
        "the blocks are not beside the suspension of the openings",
        "a text of a block composed by the dashboard",
    ]
