# ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo — Errori temporanei ritentati in ogni passo del ciclo

- Stato: proposta (23 novembre 2026)
- Requisiti: Bug 718, Task 719; R1.2.3, R1.2.4
- Collegate: estende ADR ritentativo-del-modello-nel-ciclo a ogni passo del ciclo; ADR permanenza-decisa-dall-errore-base,
  ADR 0104 (ciclo come grafo LangGraph), ADR 0064 e 0075 (confronto delle posizioni); sostituisce la regola «Fail fast:
  … senza nuovi tentativi» di `.claude/rules/context-flows.md` per gli errori temporanei
- Verifica: prova

## Contesto e problema

Il 17/11/2026 il proprietario ha deciso: ogni errore temporaneo del ciclo si ritenta nello stesso ciclo («Riprova
sempre»). ADR ritentativo-del-modello-nel-ciclo l'ha realizzato solo per la chiamata al modello. Il 23/11/2026 alle
02:50 UTC il flusso «ETH + SOL + BTC #1» ha avuto un solo errore di lettura dell'exchange al passo `read_flow_state`. Il
ciclo è fallito subito e il successivo è partito un'ora dopo, quando le condizioni per aprire non c'erano più.

## Fattori decisionali

- Decisione del proprietario (17/11/2026, ribadita il 23/11/2026): ritentare nello stesso ciclo ogni errore temporaneo.
- La permanenza la decide l'errore base: un errore permanente non si ritenta e mette in pausa come oggi (R1.2.4).
- Un ordine non si apre mai due volte: un invio fallito per un errore di rete può essere arrivato all'exchange.
- `domain` e `application` non usano librerie tecniche: l'attesa passa da una porta, come nel ritentativo del modello.
- Una fonte che non risponde resta assente senza far fallire il ciclo (R1.2.5).

## Decisione

- **Stessa politica del modello per ogni passo**: un `AutotradingError` non permanente sollevato da una porta di un passo
  del ciclo si ritenta fino a 2 volte dopo il primo tentativo, con attese di 5 e 15 secondi. Un errore permanente esce
  subito. Dopo l'ultimo tentativo esce l'ultimo errore, e il ciclo fallisce come oggi.
- **Una politica sola, in application**: un componente di `application/flows` (es. `TransientRetry` col caso d'uso che
  lo usa) riceve la porta d'attesa e ripete una chiamata. Lo usano:
  - la lettura dello stato del flusso, con la riconciliazione e il secondo confronto di ADR 0075;
  - la composizione del contesto;
  - l'aggiornamento del registro a fine ciclo;
  - ogni altra porta di un passo che oggi fa fallire il ciclo con un errore temporaneo.

  La chiamata al modello tiene il suo ritentativo (ADR ritentativo-del-modello-nel-ciclo) e non si ritenta due volte.
  Le fonti restano assenti senza ritentativo del ciclo. La porta d'attesa di `flows` si dichiara in
  `application/flows/ports.py` e la realizza `SystemClockPauseAdapter`, che oggi realizza quella di `agent`.
- **Ordini idempotenti**: l'invio di un ordine fallito per un errore temporaneo si ritenta con lo stesso `cloid`. Prima
  di reinviarlo, il contesto `orders` chiede all'exchange l'ordine con quel `cloid`:
  - se l'exchange lo conosce, si usa il suo esito e l'ordine non parte di nuovo;
  - solo se non lo conosce, si reinvia.

  Gli ordini già eseguiti dello stesso ciclo non si reinviano mai: si ritenta il solo invio fallito, non il passo
  intero. La lettura per `cloid` la realizza l'adapter Hyperliquid con l'SDK, e la sequenza sta nel caso d'uso di
  `orders`.
- **Registro**: ogni tentativo fallito si vede nel registro del ciclo (passo, errore, numero del tentativo), come i
  tentativi del modello.
- La regola «Fail fast» di `.claude/rules/context-flows.md` si aggiorna: il ciclo si interrompe al primo errore
  permanente o al terzo errore temporaneo dello stesso passo.
- Prova:
  - unit test della politica;
  - uno scenario in F1.2: errore temporaneo dell'exchange, poi lettura riuscita, ciclo completato; tre errori
    temporanei, ciclo fallito; errore permanente, nessun nuovo tentativo e flusso in pausa;
  - un test dell'invio ritentato: l'ordine che l'exchange conosce già non si reinvia; quello che non conosce si reinvia
    con lo stesso `cloid`.

## Alternative scartate

- `RetryPolicy` di LangGraph sui nodi: ritenterebbe il nodo intero, e il nodo degli ordini reinvierebbe anche gli ordini
  già eseguiti. Inoltre le attese uscirebbero dalla porta e i test aspetterebbero davvero.
- Ritentativo negli adapter: due politiche diverse, e tentativi invisibili al registro del ciclo (stesso motivo di ADR
  ritentativo-del-modello-nel-ciclo).
- Ciclo ripetuto da capo dopo un errore: richiama il modello e ne paga di nuovo il costo.

## Conseguenze

- Un ciclo con errori temporanei può durare fino a 20 secondi in più per ogni passo che li incontra.
