"""ADR-impostazioni-entra-dell-accesso-mcp-riproducibili: the Entra settings are applied by the owner with his own
identity, never by the pipeline. No workflow, action or other script of the installations changes an Entra application
(`az ad app`): the script of the owner is the only place that does.
"""

from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
OWNER_SCRIPT = REPOSITORY / "deploy" / "entra" / "configure-mcp-access.sh"
FOLDERS = (REPOSITORY / ".github", REPOSITORY / "deploy")
ENTRA_APPLICATION_COMMAND = "az ad app"


def files_changing_entra() -> list[Path]:
    return [
        path
        for folder in FOLDERS
        for path in sorted(folder.rglob("*"))
        if path.is_file() and ENTRA_APPLICATION_COMMAND in path.read_text(encoding="utf-8", errors="ignore")
    ]


def test_adr_impostazioni_entra_only_the_script_of_the_owner_changes_entra() -> None:
    assert files_changing_entra() == [OWNER_SCRIPT]


def test_adr_impostazioni_entra_the_pipeline_folders_are_searched() -> None:
    assert all(folder.is_dir() for folder in FOLDERS)
    assert (REPOSITORY / ".github" / "workflows").is_dir()
