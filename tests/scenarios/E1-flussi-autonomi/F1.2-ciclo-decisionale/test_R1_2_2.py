from pytest_bdd import scenarios

# The steps of the cycle scenarios are shared by the five requirements of F1.2.
from tests.support.cycle_steps import *  # noqa: F403

scenarios("E1-flussi-autonomi/F1.2-ciclo-decisionale/R1.2.2-nessuna-sovrapposizione-tra-cicli.feature")
