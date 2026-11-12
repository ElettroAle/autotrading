from pytest_bdd import scenarios

# A cycle of a real flow on the bridges the worker uses (ADR 0042), with the market data of the exchange.
from tests.support.flow_cycle_steps import *  # noqa: F403
from tests.support.market_source_steps import *  # noqa: F403

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.3-indicatori-tecnici.feature")
