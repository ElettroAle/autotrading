"""The scenarios of R5.1.5 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_1_5 import *  # noqa: F403 - the steps of R5.1.5, shared by its files

scenarios(
    "E5-evoluzioni/F5.1-nuove-fonti/R5.1.5-forecast-su-orizzonti-lunghi/api/R5.1.5-forecast-su-orizzonti-lunghi.feature"
)
