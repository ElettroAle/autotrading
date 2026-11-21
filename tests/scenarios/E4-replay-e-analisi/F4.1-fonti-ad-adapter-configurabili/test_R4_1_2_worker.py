"""The scenarios of R4.1.2 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r4_1_2 import *  # noqa: F403 - the steps of R4.1.2, shared by its files

scenarios(
    "E4-replay-e-analisi/F4.1-fonti-ad-adapter-configurabili/R4.1.2-credenziali-degli-adapter-delle-fonti/worker/R4.1.2-credenziali-degli-adapter-delle-fonti.feature"
)
