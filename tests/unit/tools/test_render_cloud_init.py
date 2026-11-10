from pathlib import Path

import pytest

from tools.render_cloud_init import MissingProvisioningValueError, main, render

TEMPLATE = "runcmd:\n  - tailscale up --auth-key=${TAILSCALE_AUTH_KEY} --hostname=autotrading-${ENVIRONMENT}\n"
VALUES = {
    "ENVIRONMENT": "dev\n",
    "TAILSCALE_AUTH_KEY": " tskey-auth-k123-abc ",
}


def test_values_are_trimmed_and_substituted() -> None:
    rendered = render(TEMPLATE, VALUES)

    assert "--auth-key=tskey-auth-k123-abc " in rendered
    assert "--hostname=autotrading-dev\n" in rendered


@pytest.mark.parametrize("missing", ["ENVIRONMENT", "TAILSCALE_AUTH_KEY"])
def test_missing_value_raises_typed_error(missing: str) -> None:
    with pytest.raises(MissingProvisioningValueError) as raised:
        render(TEMPLATE, {**VALUES, missing: " "})

    assert raised.value.name == missing


def test_versioned_template_renders(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for name, value in VALUES.items():
        monkeypatch.setenv(name, value)
    monkeypatch.chdir(Path(__file__).resolve().parents[3])

    assert main(["deploy/cloud-init.yaml"]) == 0
    output = capsys.readouterr().out
    assert "--auth-key=tskey-auth-k123-abc " in output
    assert "--advertise-tags=tag:autotrading-dev " in output
    assert "ssh_authorized_keys" not in output
