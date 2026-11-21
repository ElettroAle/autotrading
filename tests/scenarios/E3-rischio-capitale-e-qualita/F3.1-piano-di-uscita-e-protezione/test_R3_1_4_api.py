"""The scenarios of R3.1.4 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r3_1_4 import *  # noqa: F403 - the steps of R3.1.4, shared by its files

scenarios(
    "E3-rischio-capitale-e-qualita/F3.1-piano-di-uscita-e-protezione/R3.1.4-confidenza-e-soglia-minima/api/R3.1.4-confidenza-e-soglia-minima.feature"
)
