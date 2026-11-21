# ADR chiusure-dei-flussi-con-il-flusso-nell-ordine — Gli ordini di chiusura di stop, incasso ed emergenza portano il flusso

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 684; R1.1.5, R1.6.3, R1.7.2, R3.2.3
- Collegate: sostituisce in parte ADR 0063 (punto «senza flusso (comando manuale, stop) il flusso che ha l'asset»);
  ADR 0055 (stop di un flusso), ADR 0064 (blocco su posizione diversa), ADR incasso-dei-profitti, ADR
  chiusura-di-emergenza-per-ambito
- Verifica: prova

## Contesto e problema

Lo stop di un flusso, l'incasso e la chiusura di emergenza chiudono le posizioni con `CloseFlowPositionsUseCase`, che
chiede al worker la stessa chiusura del comando manuale (`POST /tenants/{t}/accounts/{a}/positions/{coin}/close`,
`adapters/inbound/api/worker.py`): l'ordine è registrato con origine `comando manuale` e senza `flow_id`. L'ADR 0063
attribuisce un ordine della piattaforma senza flusso al flusso che ha l'asset quando il registro scrive l'esecuzione,
e il registro si aggiorna solo al ciclo successivo di un flusso dello stesso conto. Su dev (21/11/2026) BTC è passato a
un altro flusso tra lo stop di «BTC #1» e la riconciliazione: le esecuzioni della chiusura sono finite nel flusso
nuovo, il registro di «BTC #1» è rimasto short e quello del flusso nuovo long, e il flusso nuovo va in pausa a ogni
ciclo con `FlowPositionMismatchError`.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): gli ordini di chiusura di stop, incasso ed emergenza portano
  il flusso; origine «comando manuale» con l'utente; la chiusura manuale dalla dashboard resta com'è.
- ADR 0063: un ordine della piattaforma con flusso va al suo flusso; la regola esiste già e non cambia.
- `CLAUDE.md`: niente ponti tra contesti; il contesto che usa un dato dichiara la porta, l'adapter della tecnologia la
  realizza.

## Decisione

- **Dominio `orders`**: `OrderSource` ha in più `closing_flow_id: UUID | None`, il flusso di cui l'ordine chiude la
  posizione quando non nasce da un ciclo (stop, incasso, emergenza). `FlowLink` resta il legame con ciclo e decisione
  degli ordini del ciclo. Un `OrderSource` con `flow` e `closing_flow_id` insieme è un errore tipizzato del dominio.
- **Contesto `flows`**: `PositionToClose` ha in più `flow_id`; `CloseFlowPositionsUseCase` lo valorizza con il flusso
  che chiude.
- **Contesto `orders`**: `CloseFlowPositionUseCase` (dietro `FlowPositionsPort`) e `CloseExchangePositionCommand`
  portano il flusso fino all'`OrderSource` (`OrderOrigin.MANUAL`, utente, `closing_flow_id`).
- **Worker**: la richiesta della chiusura ha `flow_id` facoltativo (`WorkerPositionClosingAdapter` lo invia, la rotta
  del worker lo passa al comando); senza `flow_id` è la chiusura manuale di oggi.
- **SQLAlchemy**: `order_repository.py` scrive `orders.flow_id` dal `FlowLink` o da `closing_flow_id`;
  `cycle_planned_at` e `decision_asset` restano nulli per una chiusura. Nessuna colonna nuova.
- **Registro (ADR 0063)**: invariato nel codice; l'esecuzione di una chiusura di stop, incasso o emergenza va al flusso
  dell'ordine. «Senza flusso il flusso che ha l'asset» resta solo per la chiusura manuale dalla dashboard e per gli
  ordini senza flusso già registrati.
- Gli ordini di chiusura di un flusso compaiono tra gli ordini del flusso (registro delle operazioni, R1.6.3) senza
  ciclo: le letture che uniscono ordini e cicli li accettano senza ciclo.

## Alternative scartate

- Aggiornare il registro del conto subito dopo lo stop: riduce la finestra ma non la chiude (un'esecuzione pubblicata in
  ritardo dall'exchange resta esposta); non richiesto dal proprietario.
- Attribuzione per asset secondo il possesso all'istante dell'esecuzione (storico delle versioni della configurazione):
  più generale, molto più lavoro, scartata dal proprietario.
- Origine nuova `OrderOrigin.FLOW` per le chiusure: perderebbe l'utente che ha dato il comando (R0.3.2).

## Conseguenze

- Uno stop seguito dallo spostamento dell'asset su un altro flusso, prima del ciclo successivo, lascia il registro del
  flusso fermato a zero e quello dell'altro flusso intatto; lo stesso per incasso ed emergenza.
- I dati già scritti con l'attribuzione sbagliata si sanano con la migrazione dell'ADR
  riparazione-delle-chiusure-attribuite-a-un-altro-flusso.

## Prove

- Scenario in R1.1.5: «Lo stop attribuisce la chiusura al flusso fermato anche se l'asset passa a un altro flusso»;
  scenari equivalenti in R3.2.3 (emergenza) e nella User Story dell'incasso; scenario della chiusura manuale invariato.
- Unit test di `OrderSource`, del caso d'uso di chiusura e del repository degli ordini; test di integrazione del
  repository contro PostgreSQL (`orders.flow_id` valorizzato, ciclo nullo).
