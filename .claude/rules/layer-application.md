---
paths:
  - "src/autotrading/application/**"
  - "tests/unit/application/**"
---

# Livello application

Contiene i casi d'uso (cosa sa fare il sistema) e le porte (cosa serve al sistema dal mondo esterno).

## Casi d'uso

- Un caso d'uso per modulo: `application/<contesto>/<verbo>_<oggetto>.py`.
- Classe `<Verbo><Oggetto>UseCase` con le dipendenze (solo porte) nel costruttore e un solo metodo
  pubblico `execute(command)`.
- Il comando è una dataclass frozen `<Verbo><Oggetto>Command` nello stesso modulo.
- `execute` si legge come una sequenza di passi nominati: decide l'ordine e i casi d'errore,
  delega le regole al domain e l'I/O alle porte.
- Nessun `tenant_id` nei comandi né nei metodi delle porte dei dati posseduti: le porte arrivano già
  legate al tenant (vedi `context-tenancy.md`).
- Un caso d'uso non istanzia adapter e non legge configurazione: tutto arriva dal costruttore.

## Porte

- `application/<contesto>/ports.py`: `typing.Protocol` con suffisso `Port`.
- Una porta dice il bisogno nel linguaggio del contesto (`read_balance`, `place_market_order`),
  mai nel linguaggio della tecnologia (`post_exchange_action`, `execute_sql`).
- I tipi in ingresso e uscita di una porta sono tipi del domain o dataclass di application, mai tipi
  di una libreria.
- Gli errori che un adapter può sollevare sono dichiarati in `application/<contesto>/errors.py`
  (es. `ExchangeUnavailableError`, `AccountNotFoundError`), sottoclassi di `ApplicationError`.
  Fanno parte del contratto della porta.

## Comunicazione tra contesti

Un contesto usa un altro contesto attraverso una porta propria, collegata in `bootstrap.py` al caso
d'uso o alla porta dell'altro contesto. Nessun import diretto degli interni di un altro contesto,
tranne `tenancy`.

## Test

Unit test in `tests/unit/application/<contesto>/test_<caso_d_uso>.py`: si costruisce il caso d'uso
con gli adapter finti di `tests/fakes/` e si verifica ogni ramo, compresi gli errori delle porte.
