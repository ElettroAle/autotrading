"""R6.4.6: the short periods, computed on the use cases (ADR periodi-brevi-come-durata-nel-dominio). playwright-bdd runs
the same scenarios on the pages of the dashboard (ADR periodi-brevi-nel-selettore-condiviso).
"""

from pytest_bdd import scenarios

from tests.support.period_steps import *  # noqa: F403

scenarios(
    "E6-piattaforma-e-operativita/F6.4-dashboard-su-mobile/R6.4.6-periodi-brevi-nel-filtro/api/R6.4.6-periodi-brevi-nel-filtro.feature"
)
