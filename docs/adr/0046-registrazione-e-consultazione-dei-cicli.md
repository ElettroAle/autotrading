# ADR 0046 — Registrazione e consultazione dei cicli

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.7.1, R1.7.3, R1.4.6 (Task T1.7.1.1, T1.7.3.1, T1.4.6.1)

## Contesto

Ogni ciclo va registrato con tutto ciò che lo ha prodotto: lo stato e la configurazione del flusso letti
all'inizio, i dati raccolti, il contesto inviato all'agente, la risposta integrale, le decisioni, l'esito del
rischio per ogni decisione, gli ordini con l'esito reale, il costo della chiamata al modello e lo stato del
flusso a fine ciclo (R1.7.1). Un ciclo fallito registra ciò che ha prodotto fino al passo dell'errore. L'utente
consulta i cicli di un suo flusso, dal più recente e a pagine di 50, e il dettaglio di ciascuno (R1.7.3), e il
costo delle chiamate per flusso, totale e per giorno UTC (R1.4.6).

Per ADR 0041 i dati che passano tra i passi del ciclo sono opachi (`object`) per `cycles`: solo i contesti dietro
le porte sanno che cosa contengono. ADR 0041 prevede già la tabella dei cicli con il vincolo di unicità su
(flusso, istante previsto) come versione reale di `CycleRepositoryPort.claim`.

## Decisione

- **Documento per passo**: `CycleRecord` porta, per ogni passo eseguito, uno `StepDocument(step, content)` con il
  risultato del passo come dati JSON, e il `CallCost` della chiamata al modello (token in ingresso, in uscita,
  costo in USD o `None` se nessuno lo conosce).
- **Chi descrive**: una porta nuova di `cycles`, `CycleJournalPort`, con `describe(step, result)` e
  `call_cost(decision)`. `RunCycleUseCase` la chiama dopo ogni passo riuscito, così un ciclo fallito ha i
  documenti dei soli passi completati. L'adapter della porta vive nel ponte di integrazione in `bootstrap.py`,
  perché solo lì si conoscono i tipi di `flows`, `sources`, `agent` e `orders`; tocca a lui non mettere mai una
  credenziale in un documento.
- **Ritocchi alle porte dei passi**: `RiskPort.check` restituisce un `RiskReview` con gli ordini approvati e gli
  esiti di tutte le decisioni (anche bloccate e scartate, che non diventano ordini); `FlowStatePort.update`
  restituisce lo stato del flusso a fine ciclo.
- **Tabella `cycles`** (migrazione 0010) con chiave (flusso, istante previsto), RLS per tenant e
  `SqlAlchemyCycleRepositoryAdapter` legato al tenant: `claim` è un `INSERT ... ON CONFLICT DO NOTHING`, la
  registrazione un `INSERT ... ON CONFLICT DO UPDATE` sulla riga presa; finché l'esito è vuoto il ciclo è in
  corso e non si mostra. I documenti sono JSONB; importi, identificativi e istanti diventano testo, e un valore
  che non è JSON solleva `UnrecordableDocumentError` invece di finire nella registrazione. Al ruolo applicativo
  solo `SELECT`, `INSERT`, `UPDATE`: un ciclo non si cancella.
- **Consultazione**: `ListCyclesUseCase` (pagina da 1, 50 cicli, si chiede un ciclo in più per sapere se segue
  un'altra pagina), `ReadCycleUseCase` per istante previsto, `ReadFlowCostUseCase` con `FlowCost.of` nel domain
  (somma dei costi noti per giorno UTC; le chiamate senza costo si contano a parte, mai stimate). Un flusso di un
  altro tenant risponde "flusso non trovato" come uno inesistente, tramite `FlowDirectoryPort`, collegata a
  `flows` dal ponte `FlowDirectoryFromFlows`. Rotte: `GET /flows/{id}/cycles?page=`,
  `GET /flows/{id}/cycles/{istante previsto}`, `GET /flows/{id}/cost`.

## Alternative scartate

- **Payload tipizzati da `cycles`** (contesto, decisioni, ordini come tipi propri): `cycles` dovrebbe importare
  gli altri contesti, contro ADR 0026 e ADR 0041.
- **Serializzare gli oggetti opachi con `repr` o `pickle`**: illeggibili per l'utente, fragili tra versioni e
  senza alcun controllo sulle credenziali.
- **Una tabella per passo**: nessuna interrogazione per passo è richiesta (l'interrogazione dello storico è fuori
  ambito in R1.7.1) e ogni lettura del dettaglio diventerebbe una giunzione su sette tabelle.
- **Paginazione a cursore**: R1.7.3 chiede pagine numerate di 50; l'indice sulla chiave primaria basta.
- **Costo totale tenuto come contatore sul flusso**: duplica un dato già nei cicli e va riallineato a ogni
  correzione; la somma per giorno sui cicli del flusso è immediata.

## Conseguenze

- Il ponte di integrazione dei cicli deve fornire l'adapter di `CycleJournalPort` che descrive i risultati di
  ogni contesto (versione della configurazione, modello, pesi, dati, contesto, risposta, esiti del rischio,
  ordini, stato finale) e il costo da `ModelUsage`, e l'adapter di `RiskPort` che restituisce il `RiskReview`.
- Lo scenario "Ciclo concluso registrato per intero" (R1.7.1) e i tre scenari sul costo della singola chiamata
  (R1.4.6) restano `@wip` fino al ponte: con le porte finte proverebbero solo l'adapter finto.
- Lo scenario "Elenco dei flussi" (R1.7.3) resta `@wip`: ultimo e prossimo ciclo nell'elenco richiedono l'istante
  di avvio del flusso (R1.1.4) e il ponte.
- Il worker che registra un ciclo usa l'adapter legato al tenant del flusso: il ponte che pianifica i flussi di
  tutti i tenant deve conoscere il tenant di ciascuno.
