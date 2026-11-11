from autotrading.domain.sources.source_definition import SourceDefinition

# Two different indices with the same name and their own methodology: the owner wants both (R1.3.6).
SENTIMENT_ALTERNATIVE_ME = SourceDefinition(
    name="sentiment-alternative-me",
    description="Crypto Fear & Greed Index di alternative.me: valore, classificazione e istante di aggiornamento.",
    per_asset=False,
    parameters=(),
)

SENTIMENT_COINMARKETCAP = SourceDefinition(
    name="sentiment-coinmarketcap",
    description="CMC Crypto Fear and Greed Index di CoinMarketCap: valore, classificazione e istante di aggiornamento.",
    per_asset=False,
    parameters=(),
)
