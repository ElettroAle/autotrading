from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter

NEWS = SourceDefinition(
    name="notizie",
    description="Notizie cripto più recenti, con titolo, data e ora di pubblicazione e sintesi.",
    per_asset=False,
    parameters=(
        SourceParameter("numero_notizie", "numero notizie", default=10, minimum=1, maximum=50),
        SourceParameter("eta_massima_ore", "età massima ore", default=24, minimum=1, maximum=168),
    ),
)
