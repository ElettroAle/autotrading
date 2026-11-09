---
paths:
  - "src/autotrading/adapters/outbound/libsodium/**"
  - "tests/unit/adapters/libsodium/**"
  - "tests/integration/libsodium/**"
---

# Adapter in uscita: libsodium

- PyNaCl, importato solo in questa cartella. Cifratura asimmetrica con `SealedBox` (ADR 0007).
- `SodiumCredentialSealerAdapter` riceve dal costruttore la sola chiave pubblica e la sua versione;
  `SodiumCredentialOpenerAdapter` riceve le chiavi private per versione, lette da file montati in
  sola lettura. **Mai variabili d'ambiente.**
- Il testo in chiaro cifrato contiene tenant, conto e credenziali; l'opener rifiuta un testo il cui
  tenant o conto non coincide con quello richiesto.
- Il risultato salvato porta sempre la versione della chiave usata; l'opener sceglie la chiave
  privata in base a quella versione.
- I permessi di ciascuna identità sono in `docs/architecture.md` §8.2: `api` riceve solo il sealer,
  il `worker` l'opener.
- Le eccezioni di PyNaCl si traducono negli errori del contratto della porta.
- Le credenziali in chiaro e le chiavi non compaiono in log, errori o repr.
