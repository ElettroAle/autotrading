---
paths:
  - "src/autotrading/adapters/outbound/json/**"
  - "tests/unit/adapters/json/**"
---

# Adapter in uscita: file JSON di configurazione

- Solo la libreria standard (`json`, `importlib.resources`): i file viaggiano nel pacchetto, accanto al
  modulo che li legge.
- `models.json` è il catalogo dei modelli IA (ADR 0030). `load_model_catalog` lo traduce nei tipi del domain
  `agent`: i numeri si leggono come `Decimal`, mai come `float`.
- Un file malformato ferma l'avvio (`InvalidModelCatalogError`); un modello o un parametro incoerente ferma
  l'avvio con l'errore del domain. Mai un catalogo parziale.
- Un fornitore nuovo nel catalogo richiede anche il suo controllo della chiave in
  `adapters/outbound/httpx/provider_key_verifier.py` (ADR 0029): un test di bootstrap lo verifica.
