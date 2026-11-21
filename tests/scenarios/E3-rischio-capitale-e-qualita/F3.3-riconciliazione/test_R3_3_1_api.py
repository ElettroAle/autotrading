"""The scenarios of R3.3.1 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r3_3_1 import *  # noqa: F403 - the steps of R3.3.1, shared by its files

scenarios(
    "E3-rischio-capitale-e-qualita/F3.3-riconciliazione/R3.3.1-allarme-sul-saldo-non-spiegato/api/R3.3.1-allarme-sul-saldo-non-spiegato.feature"
)
