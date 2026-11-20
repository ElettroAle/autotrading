from autotrading.domain.sources.source_definition import SourceDefinition

# The number of posts is a parameter of every adapter of the source, which declares its default and its range: the
# reading keeps at most that many of them (R5.1.3, ADR fonte-social-con-adapter-lunarcrush).
POSTS = "numero_messaggi"

SOCIAL = SourceDefinition(
    name="social",
    description=(
        "Cosa si dice di ogni asset del flusso sui social: sentiment, volume di menzioni e interazioni delle ultime 24 "
        "ore e i messaggi più rilevanti dei creatori più influenti, con autore, data e testo."
    ),
    per_asset=True,
    parameters=(),
)
