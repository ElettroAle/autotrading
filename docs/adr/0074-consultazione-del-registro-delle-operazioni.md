# ADR 0074 — Consultazione del registro delle operazioni

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.1, RF-13.01; Bug 154
- Collegate: ADR 0063 (registro delle operazioni e totali correnti), ADR 0047 (importi come testo senza zeri
  finali), ADR 0027 (Problem Details)

## Contesto

L'ADR 0063 conserva lo storico completo di ogni esecuzione e di ogni pagamento di funding dei conti, nelle tabelle
`account_fills` e `account_funding`, e lascia la sua lettura da parte dell'utente a un lavoro successivo. Lo storico
cresce per tutta la vita del conto: decine di migliaia di righe non si restituiscono in una risposta sola, e una
paginazione per offset costa sempre di più man mano che si va indietro. Il proprietario ha chiesto che il registro
interno sia leggibile.

## Decisione

- **Due letture**: `GET /flows/{flow_id}/operations` restituisce le esecuzioni e i pagamenti di funding del flusso;
  `GET /accounts/{account_id}/operations` quelli del conto che non sono di nessun flusso (esecuzioni non attribuite,
  funding senza flusso). Un flusso o un conto di un altro tenant ha la stessa risposta di uno inesistente (404).
- **Ordine e pagine**: dalla più recente, 50 righe per pagina (`PAGE_SIZE`). La pagina è per keyset sulla terna
  (istante, origine, riga): l'origine distingue esecuzione e funding, la riga è l'identità della tabella. Si legge
  una riga in più del limite per sapere se esiste una pagina successiva.
- **Cursore**: `next` della risposta è il parametro `after` della pagina successiva; è la terna dell'ultima riga
  vista, codificata in base64 URL-safe. Un cursore illeggibile risponde 422 con il motivo "pagina delle operazioni
  non valida" (`OperationsCursorInvalidError`).
- **Filtri**: `asset`, `from` (compreso) e `to` (escluso), combinabili con `after`.
- **Righe**: istante, asset, tipo (`ordine_flusso`, `liquidazione`, `chiusura_fuori`, `non_attribuita`, `funding`),
  lato (`acquisto`/`vendita`, dal segno della quantità), quantità, prezzo, commissione, PnL realizzato, funding.
  Una riga di funding non ha lato, quantità né prezzo. Gli importi sono testo senza zeri finali (ADR 0047).
- **Domain** (`flows/operations.py`): `OperationCursor`, `Operation`, `OperationsQuery` (con `admits`, la stessa
  regola per l'adapter in memoria) e `OperationsPage.of`.
- **Porta** `FlowOperationsPort` con `of_flow` e `unattributed_of_account`; casi d'uso `ListFlowOperationsUseCase`
  (verifica che il flusso esista nel tenant) e `ListAccountOperationsUseCase`.
- **Database**: `SqlAlchemyFlowOperationsAdapter` unisce le due tabelle con `UNION ALL`, applica filtri e keyset
  con un confronto di tuple, ordina in modo decrescente e limita, dentro una transazione con il tenant impostato
  (RLS). Gli indici della migrazione 0017 su (tenant, flusso, istante) e (tenant, conto, istante) servono la lettura;
  nessuna migrazione nuova.

## Alternative scartate

- **Offset e limite**: il costo cresce con la profondità della pagina e una riga registrata tra due richieste fa
  saltare o ripetere righe.
- **Cursore sul solo istante**: più esecuzioni dello stesso ordine hanno lo stesso istante; una pagina che finisce in
  mezzo a loro ne perderebbe qualcuna.
- **Due risorse separate per esecuzioni e funding**: l'utente vuole vedere i movimenti del flusso in un'unica
  sequenza nel tempo.
- **Lettura dall'exchange**: conserva solo le 10000 esecuzioni più recenti (ADR 0063).

## Conseguenze

- Una pagina costa lo stesso a qualunque profondità; le pagine non saltano né ripetono righe anche se il ciclo
  registra nuove esecuzioni nel frattempo.
- Il cursore non è firmato: un cursore costruito a mano porta solo a una pagina diversa dello stesso tenant, perché
  RLS e il filtro sul flusso o sul conto restano.
- Il funding senza flusso di un conto non ha un indice per conto; è poco numeroso (un pagamento all'ora per asset con
  posizione) e la lettura resta accettabile.
