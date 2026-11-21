"""The scenarios of R6.2.1 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r6_2_1 import *  # noqa: F403 - the steps of R6.2.1, shared by its files

scenarios(
    "E6-piattaforma-e-operativita/F6.2-avvisi-e-scadenze/R6.2.1-campanello-delle-notifiche/api/R6.2.1-campanello-delle-notifiche.feature"
)
