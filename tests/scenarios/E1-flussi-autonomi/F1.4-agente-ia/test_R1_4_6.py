from pytest_bdd import scenarios

# The steps of the record and of the consultation of the cycles are shared by R1.7.1, R1.7.3 and R1.4.6.
from tests.support.record_steps import *  # noqa: F403

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.6-costo-delle-chiamate.feature")
