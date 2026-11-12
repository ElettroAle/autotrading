from pytest_bdd import scenarios

from tests.support.risk_steps import *  # noqa: F403 - the steps of the risk check, shared by the features

scenarios("E1-flussi-autonomi/F1.5-rischio-ed-esecuzione/R1.5.3-decisioni-incoerenti.feature")
