# ADR protezioni-ritentate-nel-ciclo — Protezioni e accesso al conto ritentati nel ciclo

- Stato: proposta (23 novembre 2026)
- Requisiti: Bug 720, Task 722; R1.2.3, R3.1.x (stop loss e take profit)
- Collegate: completa ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo; ADR ordini-di-protezione-sull-exchange,
  ADR permanenza-decisa-dall-errore-base
- Verifica: prova

## Contesto e problema

Dopo il Bug 718 il ciclo ritenta gli errori temporanei di letture, ordini e registro. Restano fuori:

- il piazzamento, l'aggiornamento e la cancellazione dello stop loss e del take profit;
- l'apertura dell'accesso al conto;
- la protezione delle posizioni aperte (`ProtectOpenPositions`).

Le protezioni sono ordini sull'exchange senza la ricerca per `cloid`. Un solo errore di rete lascia una posizione senza
protezione, o fa fallire il ciclo.

## Fattori decisionali

- Decisione del proprietario (17/11/2026, ribadita il 23/11/2026): ogni errore temporaneo si ritenta nello stesso ciclo.
- Lo stop loss è obbligatorio: una posizione non resta mai senza protezione per un errore che un nuovo tentativo
  assorbe.
- Una protezione non si piazza mai due volte, come un ordine (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo).

## Decisione

- La stessa politica (`TransientRetry`: 2 nuovi tentativi, 5 e 15 secondi, nessun ritentativo per un errore permanente)
  vale per l'apertura dell'accesso al conto, la protezione delle posizioni aperte e ogni invio, aggiornamento o
  cancellazione di una protezione nel ciclo.
- **Protezioni idempotenti**:
  - ogni ordine di protezione riceve un `cloid` della piattaforma prima dell'invio, come gli ordini;
  - dal secondo tentativo il contesto `orders` chiede all'exchange l'ordine con quel `cloid`, e lo reinvia solo se
    l'exchange non lo conosce;
  - una cancellazione ritentata di un ordine che l'exchange non ha più vale come riuscita;
  - un aggiornamento si ritenta come cancellazione più piazzamento, ciascuno con la sua regola.
- I tentativi falliti entrano nel registro del ciclo (`failed_attempts`), come quelli degli ordini.
- Una protezione rifiutata dall'exchange resta un esito e non si ritenta (R0.3.3).
- Prova:
  - unit test per la protezione che l'exchange conosce già (nessun reinvio), quella che non conosce (reinvio con lo
    stesso `cloid`) e la cancellazione di un ordine che non c'è più;
  - uno scenario di R1.2.3: errore temporaneo al piazzamento dello stop loss, poi riuscita, posizione protetta e ciclo
    concluso.

## Alternative scartate

- Lasciare le protezioni al ciclo successivo: la posizione resterebbe scoperta per un intervallo intero.

## Conseguenze

- Ogni ritentativo di una protezione costa una lettura in più all'exchange.
