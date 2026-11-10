import os
import sys
from string import Template

from tools.errors import PipelineError
from tools.workspace import workspace_path

REQUIRED_VALUES = ("ENVIRONMENT", "TAILSCALE_AUTH_KEY")


class MissingProvisioningValueError(PipelineError):
    def __init__(self, name: str) -> None:
        super().__init__(f"valore di provisioning mancante: {name}")
        self.name = name


def render(template: str, values: dict[str, str]) -> str:
    _require_values(values)
    return Template(template).substitute({name: values[name].strip() for name in REQUIRED_VALUES})


def _require_values(values: dict[str, str]) -> None:
    for name in REQUIRED_VALUES:
        if not values.get(name, "").strip():
            raise MissingProvisioningValueError(name)


def main(arguments: list[str]) -> int:
    template = workspace_path(arguments[0]).read_text(encoding="utf-8")
    values = {name: os.environ.get(name, "") for name in REQUIRED_VALUES}
    sys.stdout.write(render(template, values))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
