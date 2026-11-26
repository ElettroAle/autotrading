"""The scenarios of R5.5.3 that the API realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_5_3 import *  # noqa: F403 - the steps of R5.5.3, shared by its files

scenarios(
    "E5-evoluzioni/F5.5-protezione-e-contesto-dei-flussi/R5.5.3-stop-in-vigore-sempre-visibile/api/R5.5.3-stop-in-vigore-sempre-visibile.feature"
)
