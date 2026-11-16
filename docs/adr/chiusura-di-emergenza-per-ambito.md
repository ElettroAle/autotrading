# ADR chiusura-di-emergenza-per-ambito — Chiusura di emergenza per flusso, conto o tutti i flussi

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.2.3 (460), Task T3.2.3.1 (482)
- Collegate: ADR 0055 (stop di un flusso), ADR 0047 (storico delle posizioni chiuse), ADR 0036 (ciclo di vita dei
  flussi), ADR 0027 (errori che dichiarano la risposta), ADR del Task di R3.1.2 (ordini di protezione sull'exchange)
- Dipende da: R3.1.2 (ramo `feat/448-piano-di-uscita-e-protezione`), per l'annullamento degli ordini di protezione

## Contesto e problema

In una situazione critica l'utente chiude con un solo comando tutte le posizioni di un flusso, dei flussi di un
conto o di tutti i suoi flussi. Ogni flusso dell'ambito va in pausa con il motivo "chiusura di emergenza" (decisione
del proprietario sull'intervista di E3: la chiusura lascia i flussi in pausa), anche se una sua chiusura fallisce;
gli ordini di protezione si annullano; una chiusura fallita non ferma le altre.

## Fattori decisionali

- R3.2.3 e decisione del proprietario: i flussi restano in pausa e riprendono solo per comando (R1.1.4).
- ADR 0055: lo stop chiude già le posizioni di un flusso dopo aver atteso il ciclo in corso, registra ogni chiusura
  nello storico con il motivo e la notifica, e riporta le posizioni rimaste aperte.
- R1.6.2: le posizioni che nessun flusso possiede non si toccano.
- Componenti riusabili dove possibile (decisione del proprietario, 16/11/2026): nessuna seconda copia della chiusura
  delle posizioni di un flusso.
- Multi-tenancy: flussi e conti di un altro tenant non esistono per la richiesta (RLS).

## Opzioni considerate

1. **Chiusura delle posizioni di un flusso estratta e condivisa con lo stop.** La sequenza oggi privata di
   `StopFlowUseCase` (attendi il ciclo, chiudi ogni asset posseduto, registra chiusura e notifica, raccogli le
   rimaste aperte) diventa un caso d'uso `CloseFlowPositionsUseCase`, con il motivo nel comando; lo stop e la
   chiusura di emergenza lo usano entrambi.
2. Chiamare `StopFlowUseCase` per ogni flusso: scartata, lo stop porta il flusso in "fermo" e non in pausa.
3. Una copia della chiusura nel nuovo caso d'uso: scartata, duplicato.

## Esito della decisione

Opzione 1.

- Domain (`flows`): `CloseReason.EMERGENCY = "chiusura di emergenza"`; un ambito (flusso, conto, tutti); un esito
  per flusso con le posizioni chiuse e quelle non chiuse con il motivo, e "nessuna posizione da chiudere" quando il
  flusso non ne ha.
- `CloseInEmergencyUseCase`: risolve i flussi dell'ambito tra quelli attivi o in pausa (un flusso o un conto
  inesistenti per il tenant sollevano gli errori 404 già esistenti); per ogni flusso mette in pausa con il motivo
  quelli attivi (attraverso `AutomaticPausePort`, così nessun ciclo nuovo apre), annulla gli ordini di protezione
  con la porta introdotta da R3.1.2, chiude le posizioni con `CloseFlowPositionsUseCase` e motivo
  `EMERGENCY`; un flusso già in pausa resta in pausa col suo motivo. Gli errori di una chiusura si raccolgono
  nell'esito e non interrompono gli altri flussi.
- Registrazione: una tabella nuova `emergency_closings` (tenant, istante, ambito, esito in JSON) sotto RLS, con
  migrazione e una porta `EmergencyClosingLogPort` realizzata dall'adapter `sqlalchemy`.
- Anteprima per la conferma (ADR chiusura-di-emergenza-nella-dashboard): `PreviewEmergencyClosingUseCase` conta i
  flussi dell'ambito e le loro posizioni aperte, così la dashboard non calcola nulla.
- API: `POST /flows/emergency-closings` con `flow_id` o `account_id` facoltativi (nessuno = tutti i flussi)
  risponde l'esito per flusso; `GET /flows/emergency-closings/preview` con gli stessi parametri risponde numero di
  flussi e di posizioni.

Verifica: prova (scenari di R3.2.3 con adapter finti, unit test dei casi d'uso e del domain, test di integrazione
della registrazione con la RLS, scenari esistenti dello stop ancora verdi dopo l'estrazione).

### Conseguenze

- Stop e chiusura di emergenza condividono un solo modo di chiudere le posizioni di un flusso.
- Lo sviluppo parte dopo che R3.1.2 è nel ramo (merge di `feat/448-piano-di-uscita-e-protezione` o di `main`).
