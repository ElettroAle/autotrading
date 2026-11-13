# ADR 0094 — Il ciclo decisionale appartiene al contesto flows

- Stato: accettata (13 novembre 2026, decisione del proprietario)
- Requisiti: R1.2.1-R1.2.5, R1.7.1, R1.7.3; Bug 170, Bug B0.0.3 (177)
- Supera: ADR 0026 nella parte che istituisce il contesto `cycles`; ADR 0041 e ADR 0082 nella parte che tiene i tipi
  del ciclo fuori dall'application e il caso d'uso del ciclo generico
- Collegate: ADR 0088 (porte del consumatore), ADR 0089 (un adapter, una tecnologia; niente ponti), CLAUDE.md
  (Regola delle dipendenze)

## Contesto e problema

Il caso d'uso del ciclo viveva nel contesto `cycles` ed era generico: i tipi che un passo passa al successivo
(lo stato del flusso, le decisioni, gli ordini approvati) contengono tipi di `flows`, e il contratto di
indipendenza vieta a `cycles` di importarli. Per questo i tipi concreti e le sequenze dei passi stavano in
`bootstrap.py`, che il test di architettura vuole senza classi né decisioni.

## Decisione (del proprietario)

- Il ciclo decisionale è del contesto `flows`: dominio in `domain/flows`, casi d'uso e porte in
  `application/flows`. Il contesto `cycles` non esiste più.
- `flows` dichiara nel proprio `ports.py` le porte verso `sources`, `agent`, `orders` e `notifications`, con i
  propri tipi ed errori: nessun contesto importa un altro (resta solo `tenancy` importabile da tutti).
- Questa prima applicazione sposta moduli, porte ed errori di `cycles` dentro `flows` senza cambiare il
  comportamento; i tipi del ciclo e le sequenze dei passi lasciano `bootstrap.py` nei passi successivi del Bug 170.

## Confronto con le decisioni scritte

- CLAUDE.md, «Struttura»: un contesto in meno; elenco dei contesti e indice delle rule aggiornati di conseguenza.
- CLAUDE.md, «Regola delle dipendenze»: rispettata, i contratti di indipendenza perdono solo `cycles`.
- `docs/architecture.md` §5 (ciclo come grafo LangGraph): non toccato da questa decisione; lo scostamento resta
  quello già registrato dall'audit.

## Conseguenze

- `context-cycles.md` confluisce in `context-flows.md`, sezione «Ciclo decisionale».
- I moduli conservano il nome: `run_cycle.py`, `cycle_record.py`, `cycle_schedule.py` stanno ora in `flows`.
