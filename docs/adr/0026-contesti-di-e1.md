# ADR 0026 — Contesti di E1: flows, cycles, sources, agent, notifications

- Stato: accettata (11 novembre 2026, decisione del proprietario)
- Requisiti: E1 (F1.1-F1.8), Task T1.1.1.1

## Contesto

E1 porta i flussi autonomi: configurazione e ciclo di vita del flusso, ciclo decisionale pianificato,
fonti dati, agente IA, controllo del rischio, attribuzione dello stato dall'exchange, registrazione e
notifiche Telegram. Nessuno dei contesti di E0 (`tenancy`, `accounts`, `orders`, `verification`) è il
posto di queste regole. `CLAUDE.md` stabilisce che un contesto nuovo nasce solo con decisione del
proprietario e porta con sé la propria rule.

## Decisione

Cinque contesti nuovi, ciascuno con la sua rule in `.claude/rules/`:

| Contesto | Copre |
|----------|-------|
| `flows` | F1.1 configurazione, versioni, stati, capitale; F1.5 limiti di rischio ed esecuzione; F1.6 attribuzione dello stato dall'exchange; R1.7.2 storico delle posizioni chiuse |
| `cycles` | F1.2 pianificazione, esclusione, errori transitori e permanenti; R1.7.1 registrazione del ciclo; R1.7.3 consultazione |
| `sources` | F1.3 catalogo, fonti, campioni |
| `agent` | F1.4 chiavi dei fornitori IA, modelli, contesto, decisione, costo |
| `notifications` | F1.8 collegamento Telegram e notifiche |

I limiti di rischio e l'attribuzione stanno in `flows` perché sono regole del flusso: si leggono e si
applicano sulla sua configurazione e sul suo stato.

L'indipendenza tra contesti, già scritta in `CLAUDE.md` e nelle rule dei livelli, diventa verificata:
due contratti import-linter `independence` (uno per `domain`, uno per `application`) su tutti i contesti
tranne `tenancy`, che resta importabile da tutti. I contratti di E0 non cambiano.

## Alternative scartate

- **Sette contesti** (`risk` e `ledger` separati da `flows`): il controllo del rischio e l'attribuzione
  lavorano solo sulla configurazione e sullo stato del flusso; separati, ogni regola chiederebbe una porta
  verso `flows` senza un confine di business reale.
- **Quattro contesti** (`cycles` dentro `flows`): pianificazione, esclusione tra processi e gestione degli
  errori sono un'altra ragione di cambiamento rispetto alla configurazione del flusso.

## Conseguenze

- I contesti comunicano solo attraverso porte collegate in `bootstrap.py`. Un identificativo di un altro
  contesto (per esempio il conto di un flusso) è un valore proprio del contesto che lo usa.
- Le cartelle `domain/<contesto>` e `application/<contesto>` esistono da subito, vuote, perché i contratti
  le nominano.
