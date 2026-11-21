"""The scenarios of R3.6.1 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r3_6_1 import *  # noqa: F403 - the steps of R3.6.1, shared by its files

scenarios(
    "E3-rischio-capitale-e-qualita/F3.6-qualita-delle-previsioni/R3.6.1-errore-medio-della-previsione/worker/R3.6.1-errore-medio-della-previsione.feature"
)
