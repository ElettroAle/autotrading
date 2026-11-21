"""R6.4.7: the last 6 hours and the whole life named «Dall'inizio», computed on the use cases (ADR
periodo-di-6-ore-e-dall-inizio). playwright-bdd runs the same scenarios on the pages of the dashboard.
"""

from pytest_bdd import scenarios

from tests.support.period_steps import *  # noqa: F403

scenarios(
    "E6-piattaforma-e-operativita/F6.4-dashboard-su-mobile/R6.4.7-periodo-di-6-ore-e-dall-inizio/api/R6.4.7-periodo-di-6-ore-e-dall-inizio.feature"
)
