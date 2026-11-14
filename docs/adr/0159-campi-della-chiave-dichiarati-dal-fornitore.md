# ADR 0159 — Campi della chiave dichiarati dal fornitore IA

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: R2.3.9 (US 281, Task 283), R1.4.1, R2.3.2
- Collegate: ADR 0158 (campi delle credenziali dell'exchange), ADR 0108 (chiave non verificata dal fornitore),
  ADR 0153, ADR 0130

## Contesto e problema

La chiave di un fornitore IA era una sola stringa. Alcuni fornitori raggiungibili da LiteLLM chiedono più dati (base
URL, versione dell'API, regione); la dashboard non può sapere quali senza nominare i fornitori.

## Opzioni considerate

### 1. Il catalogo dei modelli dichiara i campi della chiave di ogni fornitore, letti da LiteLLM

- Pro: nessuna tabella per fornitore nel codice; i campi vengono dalla libreria che chiama il modello; la dashboard
  genera il modulo come per le credenziali dell'exchange (ADR 0158).
- Contro: la deduzione dipende da `litellm.validate_environment`.

### 2. Tabella dei campi per fornitore nell'adapter

- Pro: etichette scelte a mano.
- Contro: codice per fornitore, vietato fuori da OpenRouter; da aggiornare a ogni fornitore nuovo.

## Esito della decisione

Opzione 1. `ProviderKey` è una mappa validata sui `ProviderKeyField(name, label, secret)` del fornitore
(`ProviderKeyFieldRequiredError`, `UnknownProviderKeyFieldError`); `ModelCatalog` porta i campi di ogni fornitore, con
`api_key` («Chiave API», segreto) se il fornitore non ne dichiara altri. L'adapter LiteLLM deduce i campi da
`validate_environment(model=...)["missing_keys"]` (`OPENAI_API_KEY` diventa `api_key`, `AZURE_API_BASE` diventa
`api_base`), con etichette per i parametri noti della chiamata ed è segreto ogni campo il cui nome contiene key, secret
o token; i valori passano alla chiamata come parametri omonimi. OpenRouter, unico fornitore speciale, dichiara solo
`api_key`. `GET /models` aggiunge `key_fields` a ogni fornitore; `POST /provider-keys` e `PUT /provider-keys/{p}`
ricevono `key` come mappa.

Nessuna migrazione: un sigillo vecchio `{"key": s}` si apre come `{"api_key": s}`, i nuovi contengono `{"fields": …}`.

Verifica: prova (scenario di R2.3.9, `test_provider_key.py`, `test_model_catalog.py` di dominio, LiteLLM e worker,
`test_provider_key_opener.py`, `provider-keys.test.tsx`).
