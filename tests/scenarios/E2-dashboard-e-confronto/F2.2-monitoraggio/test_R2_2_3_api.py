"""The scenarios of R2.2.3 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r2_2_3 import *  # noqa: F403 - the steps of R2.2.3, shared by its files

scenarios("E2-dashboard-e-confronto/F2.2-monitoraggio/R2.2.3-equity-curve/api/R2.2.3-equity-curve.feature")
