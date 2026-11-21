"""The scenarios of R1.3.2 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_3_2 import *  # noqa: F403 - the steps of R1.3.2, shared by its files

scenarios(
    "E1-flussi-autonomi/F1.3-fonti-dati/R1.3.2-selezione-pesi-e-parametri-delle-fonti/api/R1.3.2-selezione-pesi-e-parametri-delle-fonti.feature"
)
