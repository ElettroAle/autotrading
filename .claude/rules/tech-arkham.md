---
paths:
  - "src/autotrading/adapters/outbound/arkham/**"
  - "tests/unit/adapters/arkham/**"
  - "tests/integration/sources/test_arkham_recorded.py"
  - "tests/integration/sources/recorded/arkham/**"
---

# Adapter in uscita: Arkham

- `ArkhamWhaleTransfersAdapter` realizza `WhaleTransfersPort` della fonte `whale` con l'API Intel di Arkham
  (`GET /transfers`), filtrata per istante e controvalore minimo, con `httpx` come trasporto (ADR
  fonte-whale-con-adapter-arkham).
- Dichiarazione: nome «Arkham», campo segreto «chiave API», parametro proprio `soglia_usd` (predefinito 1.000.000, da
  100.000 a 1.000.000.000), `offers_history` vero. La chiave è del tenant (R4.1.2) e viaggia solo nell'intestazione
  `API-Key` della sua richiesta.
- Origine e destinazione si descrivono con l'entità e l'etichetta che Arkham attribuisce all'indirizzo, quando presenti.
- 401 e 403 diventano `SourceCredentialsRejectedError`, ogni altro errore, risposta irraggiungibile o di forma inattesa
  `SourceUnavailableError`; la permanenza la decide l'errore base dal codice conservato nella causa.
- `composition.py` espone `arkham_adapters()`, che crea il proprio client `httpx` sull'indirizzo dell'API;
  `configuration.py` la dataclass privata `_ArkhamSettings` con indirizzo e timeout.
- Prove su risposte HTTP registrate dalla documentazione ufficiale, senza chiave (ADR
  risposte-http-registrate-per-i-fornitori-a-chiave): `tests/integration/sources/test_arkham_recorded.py`.
