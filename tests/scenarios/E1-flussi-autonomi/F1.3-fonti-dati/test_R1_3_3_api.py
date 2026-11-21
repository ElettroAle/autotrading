"""The scenarios of R1.3.3 that the api realizes: the parameters of the source checked by the change of the flow."""

from pytest_bdd import scenarios

# The flow of the scenarios and the change of its sources, the same steps the worker file of R1.3.3 uses.
from tests.support.flow_cycle_steps import *  # noqa: F403
from tests.support.market_source_steps import *  # noqa: F403

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.3-indicatori-tecnici/api/R1.3.3-indicatori-tecnici.feature")
