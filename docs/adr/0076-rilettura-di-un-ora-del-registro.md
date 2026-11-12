# ADR 0076 — Rilettura di un'ora del registro delle operazioni

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.1, RF-13.01; Bug 166
- Collegate: ADR 0063 (registro delle operazioni e totali correnti), di cui sostituisce solo la finestra di
  rilettura

## Contesto

L'ADR 0063 legge dall'exchange, a ogni ciclo, le esecuzioni e i pagamenti di funding a partire dal cursore del
conto (l'istante dell'ultima riga registrata) meno un minuto, e scarta quelli già registrati. Una riga che
l'exchange rende disponibile più tardi di quel minuto, con un istante precedente, resta fuori dalla finestra di
ogni lettura successiva e non entra mai nel registro: i totali del flusso la perdono per sempre.

Hyperliquid espone esecuzioni (`userFillsByTime`) e funding (`userFunding`) per intervallo di tempo, con l'istante
di ciascuna riga; la documentazione non dichiara un ritardo massimo di pubblicazione. Il funding si paga a ogni
cambio d'ora, con l'istante del pagamento. Le richieste passano da nodi API diversi, che possono essere indietro
di qualche blocco l'uno rispetto all'altro: una lettura può vedere un'esecuzione più recente e non ancora una
precedente.

## Decisione

- La finestra di rilettura parte **un'ora prima del cursore** del conto, per esecuzioni e funding.
- La deduplicazione resta quella dell'ADR 0063: le chiavi già registrate nella finestra si scartano e
  l'inserimento ignora i conflitti, quindi rileggere un'ora non crea doppioni né sposta i totali.
- Il cursore resta l'istante dell'ultima riga registrata.

Un'ora copre un intero intervallo di funding e lascia un margine ampio al ritardo di un nodo API, senza cambiare
l'ordine di grandezza del lavoro: un ciclo rilegge al più un'ora di righe del conto, poche pagine anche per un conto
molto attivo, e le chiavi già registrate si leggono con l'indice per conto e istante.

## Alternative scartate

- **Lasciare un minuto**: perde in silenzio ciò che arriva in ritardo, cioè proprio l'errore che il registro deve
  impedire.
- **Rileggere tutto ciò che l'exchange conserva a ogni ciclo**: copre ogni ritardo ma rilegge fino a 10000
  esecuzioni per ciclo, il costo che l'ADR 0063 ha voluto evitare.
- **Un cursore separato per il funding**: aggiunge stato senza coprire il ritardo delle esecuzioni.

## Conseguenze

- Una riga pubblicata fino a un'ora dopo il suo istante entra nel registro una volta sola.
- Ogni ciclo legge dall'exchange e dal registro le righe dell'ultima ora del conto, anche se già registrate.
