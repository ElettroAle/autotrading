"""The scenarios of R6.2.2 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r6_2_2 import *  # noqa: F403 - the steps of R6.2.2, shared by its files

scenarios(
    "E6-piattaforma-e-operativita/F6.2-avvisi-e-scadenze/R6.2.2-avviso-di-scadenza-delle-chiavi/api/R6.2.2-avviso-di-scadenza-delle-chiavi.feature"
)
