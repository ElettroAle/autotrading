---
paths:
  - "src/autotrading/adapters/outbound/system_clock/**"
  - "tests/unit/adapters/system_clock/**"
---

# Adapter in uscita: orologio di sistema

- `SystemClockAdapter` è l'unica fonte dell'istante corrente: realizza `ClockPort` e, col metodo
  `now`, ogni orologio passato come funzione ai casi d'uso. Nessun altro modulo chiama `datetime.now`.
- Ogni istante è in UTC (`_SystemClockSettings`); `composition.py` espone `system_clock_adapters()`.
- Nei test l'orologio si sostituisce con un orologio finto, mai con un'attesa.
