"""ADR-esposizione-del-conto-nella-dashboard: the page of the account has the field of the limit of the exposure per
side, empty allowed, with its help line, the commands to set it and take it away and the reason of a refusal of the
API under it, with none of the rules of the API repeated; the form of the flow has the option of the exposure of the
other flows beside the other options of the context of the agent, with its help line.
"""

import re
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src"
ACCOUNTS = DASHBOARD / "features" / "accounts"
SETTINGS = ACCOUNTS / "components" / "account-settings.tsx"
LIMIT_FORM = ACCOUNTS / "components" / "max-direction-exposure-form.tsx"
LIMIT_REQUEST = ACCOUNTS / "api" / "set-max-direction-exposure.ts"
EDITOR = DASHBOARD / "features" / "flow-editor"
FLOW_FORM = EDITOR / "components" / "flow-form.tsx"
OPTION = EDITOR / "components" / "account-exposure-field.tsx"
LIMIT_LABEL = "Esposizione massima per direzione (% del saldo)"
OPTION_LABEL = "Esposizione degli altri flussi del conto nel contesto dell&apos;agente"
# The bound the API checks, written in the dashboard: it would repeat its rule.
REPEATED_RULE = re.compile(r"\.positive\(|\.min\(|\.gt\(|maggiore di 0|> ?0\b")


def limit_violations(settings: str, form: str, request: str) -> list[str]:
    """What keeps the limit on the page of the account, described, with both commands and the reason under it."""
    found = []
    if "<MaxDirectionExposureForm account={account} />" not in settings:
        found.append("the limit is not on the page of the account")
    field = form.find(f'label="{LIMIT_LABEL}"')
    if field < 0 or "hint={" not in form[field:]:
        found.append("the field of the limit without its help line")
    if not 0 <= field < form.find("<FormAlert"):
        found.append("the reason of a refusal is not under the field")
    found.extend(
        f"the command {command} is missing"
        for command in ("Imposta il limite", "Togli il limite")
        if command not in form
    )
    if REPEATED_RULE.search(form + request):
        found.append("a rule of the API repeated in the dashboard")
    return found


def option_violations(flow_form: str, option: str) -> list[str]:
    """What keeps the option beside the options of the memory, described."""
    found = []
    memory, shown = flow_form.find("<MemoryFields />"), flow_form.find("<AccountExposureField />")
    if not 0 <= memory < shown or "<" in flow_form[memory + len("<MemoryFields />") : shown].strip():
        found.append("the option is not beside the options of the memory")
    if OPTION_LABEL not in option or "aria-describedby" not in option:
        found.append("the option without its help line")
    return found


def test_adr_esposizione_del_conto_nella_dashboard_the_limit_is_on_the_page_of_the_account() -> None:
    found = limit_violations(
        SETTINGS.read_text(encoding="utf-8"),
        LIMIT_FORM.read_text(encoding="utf-8"),
        LIMIT_REQUEST.read_text(encoding="utf-8"),
    )

    assert found == []


def test_adr_esposizione_del_conto_nella_dashboard_a_limit_apart_with_the_rule_of_the_api_is_found() -> None:
    form = f'<FormAlert error={{errors.root}} />\n<InputField label="{LIMIT_LABEL}" />'
    request = "percent: z.string().refine((text) => Number(text) > 0, 'maggiore di 0')"

    assert limit_violations("<VirtualBalanceForm />", form, request) == [
        "the limit is not on the page of the account",
        "the field of the limit without its help line",
        "the reason of a refusal is not under the field",
        "the command Imposta il limite is missing",
        "the command Togli il limite is missing",
        "a rule of the API repeated in the dashboard",
    ]


def test_adr_esposizione_del_conto_nella_dashboard_the_option_is_beside_the_memory() -> None:
    found = option_violations(FLOW_FORM.read_text(encoding="utf-8"), OPTION.read_text(encoding="utf-8"))

    assert found == []


def test_adr_esposizione_del_conto_nella_dashboard_an_option_away_from_the_memory_without_help_is_found() -> None:
    flow_form = "<AccountExposureField />\n<MemoryFields />"

    assert option_violations(flow_form, "<input type='checkbox' /> Esposizione") == [
        "the option is not beside the options of the memory",
        "the option without its help line",
    ]
