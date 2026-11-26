"""The scenarios of R5.5.1 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_5_1 import *  # noqa: F403 - the steps of R5.5.1, shared by its files

scenarios(
    "E5-evoluzioni/F5.5-protezione-e-contesto-dei-flussi/R5.5.1-stop-che-segue-il-prezzo/worker/R5.5.1-stop-che-segue-il-prezzo.feature"
)
