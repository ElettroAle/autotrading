# ADR ritentativo-del-ciclo-entro-meta-dell-intervallo — Ritentativo del ciclo entro metà dell'intervallo

- Stato: proposta (23 novembre 2026)
- Requisiti: Bug 724, Task 725; R1.2.3
- Collegate: modifica le attese di ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo e di ADR
  protezioni-ritentate-nel-ciclo; ADR ritentativo-del-modello-nel-ciclo resta com'è
- Verifica: prova

## Contesto e problema

Il 23/11/2026 la testnet non ha risposto entro 10 secondi dalle 08:47 alle 08:51 UTC. Il ciclo delle 08:50 ha ritentato
tre volte, alle 08:50:07, 08:50:33 e 08:51:08, ed è fallito. Alle 08:55 la testnet rispondeva in meno di un secondo.
Il ritentativo di oggi copre circa un minuto: un'indisponibilità di pochi minuti fa ancora perdere il ciclo, e il
successivo parte dopo l'intervallo del flusso.

## Fattori decisionali

- Decisione del proprietario (17/11/2026, ribadita il 23/11/2026): un errore temporaneo non deve far perdere il ciclo.
- Un ciclo non deve sovrapporsi al successivo (R1.2.2): i tentativi finiscono ben prima del ciclo dopo.
- L'intervallo del flusso va da 1 minuto a 1 giorno (`CycleInterval`).

## Decisione

- `TransientRetry` fa fino a **5 nuovi tentativi** dopo il primo, con attese di **5, 15, 30, 60 e 120 secondi**. Sono
  circa 4 minuti di attese, più la durata dei tentativi.
- **Tetto**: un nuovo tentativo parte solo se dopo la sua attesa si è ancora entro **metà dell'intervallo del flusso**
  dall'istante previsto del ciclo. Altrimenti esce l'ultimo errore. Con un intervallo di 15 minuti la finestra è di 7,5
  minuti; con 1 minuto restano i tentativi che ci stanno in 30 secondi.
- L'istante corrente si legge dalla porta dell'orologio che il ciclo usa già. L'intervallo e l'istante previsto arrivano
  dal ciclo: nessuna nuova configurazione.
- Il tetto vale per ogni passo e per gli ordini e le protezioni che passano da `TransientRetry`. La chiamata al modello
  tiene i suoi 2 nuovi tentativi (ADR ritentativo-del-modello-nel-ciclo), perché ognuno costa.
- Prova:
  - unit test delle attese;
  - unit test del tetto: un intervallo breve ferma i tentativi prima della metà, uno lungo li fa tutti;
  - lo scenario di R1.2.3 «tre errori temporanei» diventa «errori temporanei per tutta la finestra»;
  - il test di architettura sulle attese si aggiorna.

## Alternative scartate

- Ritentare fino al ciclo successivo: rischio di sovrapposizione e di decisioni prese su dati ormai vecchi.
- Attese fisse senza tetto: con l'intervallo di 1 minuto il ciclo durerebbe più dell'intervallo.

## Conseguenze

- Un ciclo con l'exchange indisponibile può durare fino a metà del suo intervallo prima di fallire.
