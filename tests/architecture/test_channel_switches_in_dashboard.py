"""ADR-interruttori-dei-canali-nelle-preferenze: the channels of an event are switches, one for each channel the API
lists, never a drop-down of combinations nor a list of channels written in the panel.
"""

import re
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src"
PANEL = DASHBOARD / "features" / "notifications" / "components" / "notification-channels-panel.tsx"
# The names of the channels and of the old combinations: the panel reads the channels from the API.
CHANNEL_WORDS = re.compile(r"'(Telegram|email|entrambi|nessuno)'")

DROP_DOWN = """
const ChannelCell = ({ event, value, onChoose }) => (
  <select aria-label={`Canale di ${event}`} value={value} onChange={(change) => onChoose(change.target.value)}>
    {['Telegram', 'email', 'entrambi', 'nessuno'].map((channel) => <option key={channel}>{channel}</option>)}
  </select>
);
"""
SWITCHES = """
const ChannelSwitches = ({ channels, chosen, onChoose }) => (
  <div role="group">
    {channels.map((state) => (
      <button type="button" aria-pressed={chosen.includes(state.channel)} onClick={() => onChoose(state.channel)}>
        {state.channel}
      </button>
    ))}
  </div>
);
"""


def violations(panel: str) -> list[str]:
    """What keeps the panel from showing a switch for each channel of the API."""
    found = []
    if "<select" in panel:
        found.append("a drop-down in the panel")
    if "aria-pressed" not in panel:
        found.append("no switch with aria-pressed")
    found.extend(f"the channel {word} written in the panel" for word in CHANNEL_WORDS.findall(panel))
    return found


def test_adr_interruttori_dei_canali_nelle_preferenze_the_panel_shows_a_switch_for_each_channel_of_the_api() -> None:
    assert violations(PANEL.read_text(encoding="utf-8")) == []


def test_adr_interruttori_dei_canali_nelle_preferenze_a_drop_down_of_combinations_is_found() -> None:
    assert violations(DROP_DOWN) == [
        "a drop-down in the panel",
        "no switch with aria-pressed",
        "the channel Telegram written in the panel",
        "the channel email written in the panel",
        "the channel entrambi written in the panel",
        "the channel nessuno written in the panel",
    ]
    assert violations(SWITCHES) == []
