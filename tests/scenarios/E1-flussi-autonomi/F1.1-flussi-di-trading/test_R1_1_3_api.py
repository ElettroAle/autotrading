"""The scenarios of R1.1.3 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_1_3 import *  # noqa: F403 - the steps of R1.1.3, shared by its files

scenarios(
    "E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.3-modifica-versionata-della-configurazione/api/R1.1.3-modifica-versionata-della-configurazione.feature"
)
