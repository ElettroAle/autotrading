import os
import sys
from pathlib import Path
from string import Template

from tools.errors import PipelineError

PRIVATE_KEY_INDENT = "    "
REQUIRED_VALUES = ("DEPLOY_PUBLIC_KEY", "HOST_PRIVATE_KEY", "HOST_PUBLIC_KEY")


class MissingProvisioningValueError(PipelineError):
    def __init__(self, name: str) -> None:
        super().__init__(f"valore di provisioning mancante: {name}")
        self.name = name


def render(template: str, values: dict[str, str]) -> str:
    _require_values(values)
    return Template(template).substitute(
        DEPLOY_PUBLIC_KEY=values["DEPLOY_PUBLIC_KEY"].strip(),
        HOST_PUBLIC_KEY=values["HOST_PUBLIC_KEY"].strip(),
        HOST_PRIVATE_KEY=_indented(values["HOST_PRIVATE_KEY"]),
    )


def _require_values(values: dict[str, str]) -> None:
    for name in REQUIRED_VALUES:
        if not values.get(name, "").strip():
            raise MissingProvisioningValueError(name)


def _indented(block: str) -> str:
    return "\n".join(PRIVATE_KEY_INDENT + line for line in block.strip().splitlines())


def main(arguments: list[str]) -> int:
    template = Path(arguments[0]).read_text(encoding="utf-8")
    values = {name: os.environ.get(name, "") for name in REQUIRED_VALUES}
    sys.stdout.write(render(template, values))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
