"""The scenarios of R5.5.5 that the API realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r5_5_5 import *  # noqa: F403 - the steps of R5.5.5, shared by its files

scenarios(
    "E5-evoluzioni/F5.5-protezione-e-contesto-dei-flussi/R5.5.5-esposizione-per-direzione-tra-i-flussi-del-conto/api/R5.5.5-esposizione-per-direzione-tra-i-flussi-del-conto.feature"
)
