"""The scenarios of R5.5.6 that the MCP server realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_5_6 import *  # noqa: F403 - the steps of R5.5.6, shared by its files

scenarios(
    "E5-evoluzioni/F5.5-protezione-e-contesto-dei-flussi/R5.5.6-commissioni-nel-contesto-dell-agente/mcp/R5.5.6-commissioni-nel-contesto-dell-agente.feature"
)
