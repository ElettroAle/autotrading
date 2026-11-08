from pathlib import Path

import pytest

from tools.render_cloud_init import MissingProvisioningValueError, main, render

TEMPLATE = (
    "users: [${DEPLOY_PUBLIC_KEY}]\nssh_keys:\n  ed25519_private: |\n${HOST_PRIVATE_KEY}\n  pub: ${HOST_PUBLIC_KEY}\n"
)
VALUES = {
    "DEPLOY_PUBLIC_KEY": "ssh-ed25519 AAAA deploy\n",
    "HOST_PRIVATE_KEY": "-----BEGIN KEY-----\nabc\n-----END KEY-----\n",
    "HOST_PUBLIC_KEY": "ssh-ed25519 BBBB host",
}


def test_private_key_is_indented_inside_the_block() -> None:
    rendered = render(TEMPLATE, VALUES)

    assert "    -----BEGIN KEY-----\n    abc\n    -----END KEY-----" in rendered
    assert "users: [ssh-ed25519 AAAA deploy]" in rendered
    assert "pub: ssh-ed25519 BBBB host" in rendered


@pytest.mark.parametrize("missing", ["DEPLOY_PUBLIC_KEY", "HOST_PRIVATE_KEY", "HOST_PUBLIC_KEY"])
def test_missing_value_raises_typed_error(missing: str) -> None:
    with pytest.raises(MissingProvisioningValueError) as raised:
        render(TEMPLATE, {**VALUES, missing: " "})

    assert raised.value.name == missing


def test_versioned_template_renders(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for name, value in VALUES.items():
        monkeypatch.setenv(name, value)
    monkeypatch.chdir(Path(__file__).resolve().parents[3])

    assert main(["deploy/cloud-init.yaml"]) == 0
    assert "ssh-ed25519 AAAA deploy" in capsys.readouterr().out
