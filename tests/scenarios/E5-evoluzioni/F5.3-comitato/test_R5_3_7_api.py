"""The scenarios of R5.3.7 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_3_7 import *  # noqa: F403 - the steps of R5.3.7, shared by its files

scenarios(
    "E5-evoluzioni/F5.3-comitato/R5.3.7-memoria-del-flusso-riepilogo-e-vista-tra-asset/api/R5.3.7-memoria-del-flusso-riepilogo-e-vista-tra-asset.feature"
)
