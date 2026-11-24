"""The scenarios of R5.3.4 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_3_4 import *  # noqa: F403 - the steps of R5.3.4, shared by its files

scenarios("E5-evoluzioni/F5.3-comitato/R5.3.4-memoria-delle-decisioni/worker/R5.3.4-memoria-delle-decisioni.feature")
