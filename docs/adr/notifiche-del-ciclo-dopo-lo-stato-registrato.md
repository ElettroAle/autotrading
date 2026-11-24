# ADR notifiche-del-ciclo-dopo-lo-stato-registrato — Notifiche del ciclo inviate dopo lo stato registrato

- Stato: proposta (23 novembre 2026)
- Requisiti: Bug 729, Task 730; R3.5.4, R1.8.2
- Collegate: supera la conseguenza «una notifica emessa tra due cicli mostra lo stato dell'ultimo ciclo concluso» di ADR
  stato-del-flusso-in-ogni-notifica per le notifiche nate dentro un ciclo; ADR 0120 (equity registrata a ogni ciclo);
  ADR cache-delle-letture-del-conto-come-decorator-in-memoria (decorator in memoria in `process_memory/`); ADR
  outbox-delle-integrazioni-esterne-con-procrastinate
- Verifica: prova

## Contesto e problema

La riga di stato in fondo alle notifiche (R3.5.4) legge l'equity dell'ultimo ciclo registrato e le posizioni attese dal
registro. Le notifiche degli ordini (posizione aperta, posizione chiusa, ordine rifiutato, apertura ridotta o bloccata)
partono invece durante il ciclo, prima che il ciclo aggiorni il registro e registri l'equity.

Il 23/11/2026 in dev, al primo ciclo del flusso «Tendenza 30g», la notifica «posizione aperta» finiva con «valore non
disponibile · nessuna posizione aperta». Nei cicli successivi la riga mostra il flusso di prima dell'ordine appena
annunciato.

## Fattori decisionali

- R3.5.4: la riga di stato descrive il flusso; nella notifica di un ordine deve descriverlo dopo quell'ordine.
- R1.8.2 e ADR stato-del-flusso-in-ogni-notifica: una notifica non rallenta né fa fallire il ciclo, e non legge
  l'exchange per notificare.
- `CLAUDE.md`: una memoria di processo è un decorator della stessa porta in una cartella propria, con lo stato creato
  dalla composition e mai in variabili di modulo; niente ponti tra contesti.

## Decisione

- **Le notifiche nate in un ciclo partono a fine ciclo**: il ciclo le trattiene e le consegna dopo aver aggiornato il
  registro e registrato l'equity. Questo vale sia per il ciclo concluso sia per quello fallito (dopo il ciclo fallito
  registrato e l'eventuale equity). La riga di stato, letta con `FlowStatusPort` come oggi, vede così valore e posizioni
  dopo gli ordini del ciclo.
- **Decorator in memoria delle porte di notifica del ciclo**, in `adapters/outbound/process_memory/`:
  - realizza le stesse porte `*NoticePort` che il ciclo usa (ordini, aperture ridotte o bloccate, posizioni chiuse e le
    altre emesse dai passi del ciclo) e trattiene le notifiche nell'ordine in cui arrivano;
  - realizza una porta di `flows` (es. `CycleNoticesPort.release()`) che le consegna alla porta decorata;
  - la composition lo crea per ogni ciclo, come il ritentativo, quindi due cicli non condividono notifiche.
- `RunCycleUseCase` chiama `release()` come ultimo passo, sia del ciclo concluso sia di quello fallito, e anche quando
  rilancia un errore permanente. Un errore di consegna resta un invio fallito registrato, come oggi, e non fa fallire il
  ciclo.
- L'equity che il ciclo registra è quella dello stato letto dopo l'aggiornamento del registro, quando il ciclo arriva a
  quel passo (ADR 0120); per un ciclo che fallisce prima resta quella dell'ultimo stato letto.
- Le notifiche fuori dal ciclo (comandi manuali, stop, incasso, emergenza, notifiche del conto) partono subito come
  oggi.
- «Valore non disponibile» resta solo per un flusso senza alcuna equity registrata.
- Prova: gli scenari del Bug 729 (apertura al primo ciclo, apertura con posizioni già presenti, chiusura dell'unica
  posizione, ordine rifiutato, flusso mai girato) in R3.5.4; unit test del decorator e di `RunCycleUseCase` (consegna
  dopo l'equity, anche al ciclo fallito).

## Alternative scartate

- Leggere valore e posizioni dall'exchange al momento della notifica: vietato da R1.8.2.
- Passare lo stato del flusso dai passi del ciclo a ogni porta di notifica: scartato in ADR
  stato-del-flusso-in-ogni-notifica, e a metà ciclo il registro non è ancora aggiornato.
- Calcolare la riga alla consegna dell'outbox: la consegna può avvenire prima della fine del ciclo.

## Conseguenze

- Le notifiche di un ciclo arrivano qualche secondo dopo, a fine ciclo, tutte insieme e nell'ordine degli eventi.
- La conseguenza di ADR stato-del-flusso-in-ogni-notifica resta valida per le notifiche fuori dal ciclo.
