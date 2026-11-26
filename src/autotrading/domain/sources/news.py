from collections.abc import Mapping

from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter, SourceParameterValue, number_of

COUNT = "numero_notizie"
MAX_AGE_HOURS = "eta_massima_ore"


def no_recent_news(settings: Mapping[str, SourceParameterValue]) -> Mapping[str, str]:
    """No recent news is itself a datum for the agent (R1.3.7)."""
    hours = number_of(settings, MAX_AGE_HOURS)
    window = "nell'ultima ora" if hours == 1 else f"nelle ultime {hours} ore"
    return {"nota": f"nessuna notizia {window}"}


NEWS = SourceDefinition(
    name="notizie",
    description="Notizie cripto più recenti, con titolo, data e ora di pubblicazione e sintesi.",
    per_asset=False,
    parameters=(
        SourceParameter(
            COUNT,
            "numero notizie",
            default=10,
            minimum=1,
            maximum=50,
            description="Quante notizie, le più recenti, riceve l'agente a ogni ciclo. Da 1 a 50. Predefinito: 10.",
        ),
        SourceParameter(
            MAX_AGE_HOURS,
            "età massima ore",
            default=24,
            minimum=1,
            maximum=168,
            description="Ore oltre le quali una notizia è troppo vecchia per l'agente. Da 1 a 168. Predefinito: 24.",
        ),
    ),
    silence=no_recent_news,
)
