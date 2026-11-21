"""The scenarios of R2.4.1 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r2_4_1 import *  # noqa: F403 - the steps of R2.4.1, shared by its files

scenarios(
    "E2-dashboard-e-confronto/F2.4-confronto-tra-flussi/R2.4.1-duplicazione-di-un-flusso/api/R2.4.1-duplicazione-di-un-flusso.feature"
)
