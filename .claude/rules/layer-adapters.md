---
paths:
  - "src/autotrading/adapters/**"
  - "src/autotrading/bootstrap.py"
  - "tests/unit/adapters/**"
  - "tests/integration/**"
---

# Livello adapters e composition root

Qui vivono le tecnologie. Ogni tecnologia è incapsulata in una sola cartella.

## Adapter in uscita

- `adapters/outbound/<tecnologia>/`: implementano le porte di application.
- Nome `<Tecnologia><Ruolo>Adapter` (es. `OpenBaoSecretVaultAdapter`); rispetta la porta
  strutturalmente, verificato da mypy.
- Le eccezioni della libreria si catturano qui e si traducono subito nell'errore tipizzato del
  contratto della porta. Nessuna eccezione di libreria esce dall'adapter.
- La traduzione tra tipi della libreria e tipi del dominio sta in funzioni private piccole,
  testabili senza la tecnologia.
- Una cartella di tecnologia non importa un'altra cartella di tecnologia.
- Configurazione e segreti arrivano dal costruttore; un adapter non legge variabili d'ambiente.

## Adapter in ingresso

`adapters/inbound/api/`: traduce una richiesta esterna in un comando, chiama il caso d'uso, traduce
esito ed errori tipizzati nella risposta. Nessuna logica di business.

## bootstrap.py

- Unico punto che conosce sia le porte sia gli adapter, e unico che legge la configurazione.
- `for_tenant(tenant_id)` costruisce, per ogni richiesta, adapter legati al tenant e casi d'uso.
- Nei test gli stessi casi d'uso si costruiscono con gli adapter finti al posto di quelli veri.

## Test

- Unit test delle funzioni di traduzione in `tests/unit/adapters/<tecnologia>/`.
- Test di integrazione contro la tecnologia vera in `tests/integration/<tecnologia>/`
  (vedi `tests.md`).
