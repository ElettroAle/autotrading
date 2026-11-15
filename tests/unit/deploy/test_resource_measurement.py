"""Every release measures memory and disk of the installation and reports them in the summary (Bug 252).

Architecture proof of ADR-0162: the action starts the measure before the pull, reports it on exit after the services
are up, and the measure never fails the release.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEPLOY_ACTION = ROOT / ".github" / "actions" / "ssh-deploy" / "action.yml"
SCRIPT = ROOT / "deploy" / "measure-resources.sh"
START = "bash /opt/autotrading/measure-resources.sh start"
REPORT = "bash /opt/autotrading/measure-resources.sh report"
TRAP = "trap report_resources EXIT"
PULL = "docker compose pull"
PRUNE = "docker image prune"
SERVICES_UP = "docker compose up -d --remove-orphans --wait"
# The fake docker answers like the real one: the format of the caller with the name and the usage of two containers.
FAKE_DOCKER = """#!/usr/bin/env bash
case "$1" in
  stats)
    format="${@: -1}"
    for line in "autotrading-api-1 180.4MiB" "autotrading-postgres-1 1.5GiB"; do
      name="${line% *}"; usage="${line#* }"
      out="${format//\\{\\{.Name\\}\\}/$name}"
      printf '%s\\n' "${out//\\{\\{.MemUsage\\}\\}/$usage / 3.8GiB}"
    done ;;
  system) echo "TYPE TOTAL ACTIVE SIZE RECLAIMABLE" ;;
esac
"""
BROKEN_DOCKER = """#!/usr/bin/env bash
echo "Cannot connect to the Docker daemon" >&2
exit 1
"""
SAMPLES = """container autotrading-api-1 120MiB / 3.8GiB
container autotrading-postgres-1 900MiB / 3.8GiB
container autotrading-migrate-1 512000KiB / 3.8GiB
available 2097152
container autotrading-api-1 0.5GiB / 3.8GiB
container autotrading-postgres-1 1.75GiB / 3.8GiB
available 524288
"""
# docker stats shows a restarting container, whose stats it cannot read, as a row of dashes.
RESTARTING_SAMPLES = """container autotrading-api-1 120MiB / 3.8GiB
container -- -- / --
available 524288
"""


def _action() -> str:
    return DEPLOY_ACTION.read_text(encoding="utf-8")


def _report_function() -> str:
    action = _action()
    return action[action.index("report_resources() {") : action.index(TRAP)]


def _run_report(directory: Path, *, samples: str | None, docker: bool = True) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    assert bash is not None, "bash runs the scripts of the installation"
    bin_directory = directory / "bin"
    bin_directory.mkdir()
    # Without an answering docker the fake still shadows a real one, as on the runner: it fails like a stuck daemon.
    fake = bin_directory / "docker"
    fake.write_text(FAKE_DOCKER if docker else "#!/usr/bin/env bash\nexit 1\n", encoding="utf-8", newline="\n")
    fake.chmod(0o755)
    if samples is not None:
        (directory / "resource-samples.txt").write_text(samples, encoding="utf-8", newline="\n")
    environment = {
        **os.environ,
        "PATH": os.pathsep.join([str(bin_directory), os.environ.get("PATH", "")]),
        "MEASUREMENT_DIRECTORY": directory.as_posix(),
    }
    return subprocess.run(
        [bash, SCRIPT.as_posix(), "report"], env=environment, capture_output=True, text=True, timeout=60, check=False
    )


def _row(report: str, container: str) -> list[str]:
    match = re.search(rf"^\| {re.escape(container)} \|(.*)\|$", report, re.MULTILINE)
    assert match, f"no row for {container} in:\n{report}"
    return [cell.strip() for cell in match.group(1).split("|")]


def test_adr_0162_the_release_copies_the_measure_to_the_machine_like_the_other_scripts() -> None:
    assert re.search(r"'cat > /opt/autotrading/measure-resources\.sh' \\\n\s+< deploy/measure-resources\.sh", _action())


def test_adr_0162_the_measure_starts_before_the_pull() -> None:
    action = _action()

    assert 0 <= action.index(START) < action.index(PRUNE) < action.index(PULL)


def test_adr_0162_the_report_runs_on_exit_so_a_failed_release_still_stops_the_measure() -> None:
    action = _action()

    assert action.index(START) < action.index(TRAP) < action.index(PULL)
    assert REPORT in _report_function()


def test_adr_0162_the_report_comes_after_the_services_are_up() -> None:
    action = _action()

    assert action.count(REPORT) == 1
    assert action.index(TRAP) < action.index(SERVICES_UP)


def test_adr_0162_the_report_goes_to_the_job_summary_and_to_the_job_log() -> None:
    # The job summary has no API: the job log keeps the same report readable for the limits of Task 254.
    assert re.search(r'measure-resources\.sh report.*\n?.*\| tee -a "\$GITHUB_STEP_SUMMARY"', _report_function())


def test_adr_0162_the_measure_never_fails_the_release() -> None:
    action = _action()
    calls = [line for line in action.splitlines() if "measure-resources.sh" in line]

    assert calls
    assert [call for call in calls if "||" not in call and not call.rstrip().endswith("\\")] == []
    assert re.search(r'local status=\$\?[\s\S]*exit "\$status"', _report_function())


def test_adr_0162_a_hung_machine_does_not_block_the_release_on_the_measure() -> None:
    calls = [line for line in _action().splitlines() if "ssh" in line and "measure-resources.sh" in line]

    assert calls
    assert [call for call in calls if not re.search(r"timeout \d+ ssh", call)] == []


def test_adr_0162_the_sampler_runs_detached_every_two_seconds_under_the_installation_directory() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'directory="${MEASUREMENT_DIRECTORY:-/opt/autotrading}"' in script
    assert re.search(r"setsid nohup bash .* sample < /dev/null > /dev/null 2>&1 &", script)
    assert "sleep 2" in script
    assert "docker stats --no-stream" in script
    assert "/proc/meminfo" in script


def test_adr_0162_the_sampler_stops_by_itself_if_no_report_ever_comes() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert re.search(r'while \[ "\$SECONDS" -lt \d+ \]', script)


def test_adr_0162_the_report_stops_the_sampler_before_reading_the_samples() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "report() {\n  stop_sampler\n" in script


def test_adr_0162_the_report_shows_peak_and_rest_of_every_container_in_mebibytes(tmp_path: Path) -> None:
    completed = _run_report(tmp_path, samples=SAMPLES)

    assert completed.returncode == 0, completed.stderr
    assert _row(completed.stdout, "autotrading-api-1") == ["512", "180"]
    assert _row(completed.stdout, "autotrading-postgres-1") == ["1792", "1536"]


def test_adr_0162_a_container_that_ended_shows_its_peak_without_rest(tmp_path: Path) -> None:
    completed = _run_report(tmp_path, samples=SAMPLES)

    assert _row(completed.stdout, "autotrading-migrate-1") == ["500", "non in esecuzione"]


def test_adr_0162_the_report_shows_the_minimum_available_memory_of_the_machine(tmp_path: Path) -> None:
    completed = _run_report(tmp_path, samples=SAMPLES)

    assert "Memoria disponibile minima durante il rilascio: 512 MiB" in completed.stdout


def test_adr_0162_the_report_shows_the_disk_of_the_machine_and_of_docker(tmp_path: Path) -> None:
    completed = _run_report(tmp_path, samples=SAMPLES)

    assert re.search(r"Filesystem", completed.stdout)
    assert "TYPE TOTAL ACTIVE SIZE RECLAIMABLE" in completed.stdout


def test_adr_0162_a_report_without_samples_says_so_and_succeeds(tmp_path: Path) -> None:
    completed = _run_report(tmp_path, samples=None)

    assert completed.returncode == 0, completed.stderr
    assert "Memoria disponibile minima durante il rilascio: nessun campione" in completed.stdout
    assert _row(completed.stdout, "autotrading-api-1") == ["nessun campione", "180"]


def test_adr_0162_a_report_without_docker_still_succeeds(tmp_path: Path) -> None:
    completed = _run_report(tmp_path, samples=SAMPLES, docker=False)

    assert completed.returncode == 0, completed.stderr
    assert _row(completed.stdout, "autotrading-api-1") == ["512", "non misurato"]


def test_adr_0165_a_restarting_container_is_not_a_row_of_the_report(tmp_path: Path) -> None:
    completed = _run_report(tmp_path, samples=RESTARTING_SAMPLES)

    assert completed.returncode == 0, completed.stderr
    assert re.findall(r"^\| -- \|.*$", completed.stdout, re.MULTILINE) == []
    assert _row(completed.stdout, "autotrading-api-1") == ["120", "180"]
