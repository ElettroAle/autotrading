"""The scenarios of R3.1.1 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r3_1_1 import *  # noqa: F403 - the steps of R3.1.1, shared by its files

scenarios(
    "E3-rischio-capitale-e-qualita/F3.1-piano-di-uscita-e-protezione/R3.1.1-piano-di-uscita-nella-decisione/api/R3.1.1-piano-di-uscita-nella-decisione.feature"
)
