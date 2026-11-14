---
paths:
  - "src/autotrading/adapters/outbound/json/**"
  - "tests/unit/adapters/json/**"
---

# Adapter in uscita: file JSON di configurazione

- Solo la libreria standard (`json`, `importlib.resources`): i file viaggiano nel pacchetto, accanto al
  modulo che li legge.
- I numeri si leggono come `Decimal`, mai come `float`.
- Il catalogo dei modelli non è più un file JSON: viene dalla mappa dei modelli della libreria LiteLLM (ADR 0148).
