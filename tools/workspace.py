from pathlib import Path

from tools.errors import PipelineError


class PathOutsideWorkspaceError(PipelineError):
    def __init__(self, argument: str) -> None:
        super().__init__(f"percorso fuori dalla cartella di lavoro: {argument}")
        self.argument = argument


def workspace_path(argument: str) -> Path:
    workspace = Path.cwd().resolve()
    path = (workspace / argument).resolve()
    if not path.is_relative_to(workspace):
        raise PathOutsideWorkspaceError(argument)
    return path
