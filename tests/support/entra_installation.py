"""The Entra settings of an installation, applied by the script of the owner against an `az` that keeps its state (ADR
impostazioni-entra-dell-accesso-mcp-riproducibili).

The fake `az` stands in front of the real one on the PATH like the real one does: it shows and updates the identifiers
of an application and the redirects of its public client, keeps them between calls, and logs every call.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy" / "entra" / "configure-mcp-access.sh"

API_CLIENT_ID = "11111111-1111-1111-1111-111111111111"
MCP_CLIENT_ID = "22222222-2222-2222-2222-222222222222"
INSTALLATION_NAME = "dev.example.ts.net"
# The redirect the client had before the fix: no path, which Entra does not match with the one Claude Code sends.
REDIRECT_BEFORE_THE_FIX = "http://localhost"

FAKE_AZ = """#!/usr/bin/env bash
state="${FAKE_AZ_STATE}"
echo "$*" >> "${state}/calls.log"
if [ -n "${FAKE_AZ_FAILS:-}" ]; then
  echo "ERROR: forced failure" >&2
  exit 1
fi
[ "$1 $2" = "ad app" ] || { echo "unexpected call: $*" >&2; exit 64; }
action="$3"
shift 3
identifier=""
target=""
shown=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --id) identifier="$2"; shift 2 ;;
    --query) shown="$2"; shift 2 ;;
    --output) shift 2 ;;
    --identifier-uris) target="identifierUris"; : > "${state}/${identifier}.${target}"; shift ;;
    --public-client-redirect-uris) target="publicClient.redirectUris"; : > "${state}/${identifier}.${target}"; shift ;;
    *) echo "$1" >> "${state}/${identifier}.${target}"; shift ;;
  esac
done
if [ "$action" = "show" ]; then
  cat "${state}/${identifier}.${shown}" 2>/dev/null || true
fi
"""


@dataclass(frozen=True)
class ScriptRun:
    status: int
    output: str


class EntraInstallation:
    """The application of the API and the client of the MCP server of one installation, as the directory holds them."""

    def __init__(self, directory: Path, name: str = INSTALLATION_NAME) -> None:
        self.name = name
        self._state = directory / "state"
        self._state.mkdir()
        bin_directory = directory / "bin"
        bin_directory.mkdir()
        fake = bin_directory / "az"
        fake.write_text(FAKE_AZ, encoding="utf-8", newline="\n")
        fake.chmod(0o755)
        self._path = os.pathsep.join([str(bin_directory), os.environ.get("PATH", "")])
        self.fails = False
        self.seed(API_CLIENT_ID, "identifierUris", [f"api://{API_CLIENT_ID}"])
        self.seed(MCP_CLIENT_ID, "publicClient.redirectUris", [REDIRECT_BEFORE_THE_FIX])

    @property
    def resource(self) -> str:
        return f"https://{self.name}/mcp"

    @property
    def api_identifiers(self) -> list[str]:
        return self._read(API_CLIENT_ID, "identifierUris")

    @property
    def client_redirects(self) -> list[str]:
        return self._read(MCP_CLIENT_ID, "publicClient.redirectUris")

    @property
    def writes(self) -> list[str]:
        calls = self._state / "calls.log"
        lines = calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []
        return [line for line in lines if line.startswith("ad app update")]

    def configure(self, *arguments: str) -> ScriptRun:
        bash = shutil.which("bash")
        assert bash is not None, "bash runs the scripts of the installation"
        given = arguments or (API_CLIENT_ID, MCP_CLIENT_ID, self.name)
        environment = {**os.environ, "PATH": self._path, "FAKE_AZ_STATE": self._state.as_posix()}
        if self.fails:
            environment["FAKE_AZ_FAILS"] = "1"
        done = subprocess.run(
            [bash, SCRIPT.as_posix(), *given],
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        return ScriptRun(done.returncode, done.stdout + done.stderr)

    def _read(self, client_id: str, setting: str) -> list[str]:
        return (self._state / f"{client_id}.{setting}").read_text(encoding="utf-8").splitlines()

    def seed(self, client_id: str, setting: str, values: list[str]) -> None:
        (self._state / f"{client_id}.{setting}").write_text("\n".join(values) + "\n", encoding="utf-8", newline="\n")
