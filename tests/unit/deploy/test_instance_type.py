"""The machine follows the declared instance type at every release and provisioning (ADR 0144, Bug 250)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ACTIONS = ROOT / ".github" / "actions"
RELEASE = ROOT / ".github" / "workflows" / "reusable-release.yml"
JOB = re.compile(r"^  ([a-z_-]+):\n((?:    .*\n|\s*\n)*)", re.MULTILINE)
RESIZE = "uses: ./.github/actions/ovh-resize"
DEPLOY = "uses: ./.github/actions/ssh-deploy"
WAIT = "uses: ./.github/actions/ssh-wait"


def _release_jobs() -> dict[str, str]:
    jobs = RELEASE.read_text(encoding="utf-8").split("\njobs:\n", 1)[1]
    return {match.group(1): match.group(2) for match in JOB.finditer(jobs)}


def _deploying_jobs() -> dict[str, str]:
    return {name: body for name, body in _release_jobs().items() if DEPLOY in body}


def _action(name: str) -> str:
    return (ACTIONS / name / "action.yml").read_text(encoding="utf-8")


def test_both_installations_are_deployed_by_the_release() -> None:
    assert set(_deploying_jobs()) == {"dev", "prod"}


def test_adr_0144_every_deploy_first_aligns_the_machine_to_the_declared_instance_type() -> None:
    late = [name for name, body in _deploying_jobs().items() if not 0 <= body.find(RESIZE) < body.find(DEPLOY)]

    assert late == []


def test_adr_0144_the_release_aligns_to_the_instance_type_of_its_environment() -> None:
    flavors = [re.search(r"flavor: (.*)", body.split(RESIZE, 1)[-1]) for body in _deploying_jobs().values()]

    assert [flavor.group(1) if flavor else None for flavor in flavors] == ["${{ vars.OVH_FLAVOR || 'd2-2' }}"] * 2


def test_adr_0144_provisioning_aligns_an_existing_machine() -> None:
    step = _action("ovh-provision").split(RESIZE, 1)[0].rsplit("    - ", 1)[-1]

    assert "if: ${{ steps.exists.outputs.created == 'false' }}" in step


def test_adr_0144_the_alignment_resizes_only_a_machine_of_another_type() -> None:
    script = _action("ovh-resize")

    assert script.index('[ "$current" = "$FLAVOR" ]') < script.index("openstack server resize --flavor")
    assert "openstack server resize confirm" in script


def test_the_deploy_waits_for_a_machine_that_the_alignment_restarted() -> None:
    steps = _action("ssh-deploy").split("\n  steps:\n", 1)[1]

    assert steps.lstrip().startswith(f"- {WAIT}")
