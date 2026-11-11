---
paths:
  - "src/autotrading/domain/**"
  - "tests/unit/domain/**"
---

# Livello domain

Contiene le regole di business: entità, value object, invarianti, calcoli. È il centro dell'esagono.

## Cosa ci sta

- Entità con identità (`Account`, `Position`) e value object immutabili (`AccountId`, `Leverage`,
  `Slippage`), questi ultimi come `@dataclass(frozen=True, slots=True)`.
- Le regole che valgono a prescindere da come si arriva al sistema e da dove si salvano i dati
  (es. leva entro il massimo dell'asset, arrotondamento della dimensione al passo ammesso).
- Gli errori di dominio del contesto in `domain/<contesto>/errors.py`, sottoclassi di `DomainError`.
- `domain/errors.py`: la radice `AutotradingError` (con `status_code`, `permanent`, `details`, ADR 0027) e
  `DomainError`. Nient'altro.

## Cosa non ci sta

- Nessun import da `application`, `adapters`, `bootstrap`.
- Nessuna libreria esterna: niente pydantic, sqlalchemy, fastapi, SDK, httpx. Solo libreria standard.
- Nessun I/O: niente file, rete, orologio di sistema, variabili d'ambiente, logging di infrastruttura.
  Se serve l'ora corrente, arriva come parametro o da una porta di application.
- Nessun contesto importa un altro contesto del domain, tranne `domain/tenancy`
  (vedi `context-tenancy.md`).

## Forma

- Le invarianti si controllano nel costruttore o nel metodo che cambia lo stato: un oggetto di
  dominio non esiste mai in stato invalido.
- Un errore di dominio porta i dati che servono a capire il motivo (es. `maximum=40`), non solo un testo.
- I metodi esprimono operazioni di business (`position.close()`), non setter.

## Test

Unit test puri in `tests/unit/domain/<contesto>/test_<modulo>.py`, uno per modulo di produzione:
nessun finto necessario, nessun I/O.
