"""The scenarios of R5.1.3 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_1_3 import *  # noqa: F403 - the steps of R5.1.3, shared by its files

scenarios("E5-evoluzioni/F5.1-nuove-fonti/R5.1.3-sentiment-social/worker/R5.1.3-sentiment-social.feature")
