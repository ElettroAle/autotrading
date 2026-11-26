"""The scenarios of R5.5.4 that the API realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_5_4 import *  # noqa: F403 - the steps of R5.5.4, shared by its files

scenarios(
    "E5-evoluzioni/F5.5-protezione-e-contesto-dei-flussi/R5.5.4-dati-di-regime-nella-fonte-indicatori/api/R5.5.4-dati-di-regime-nella-fonte-indicatori.feature"
)
