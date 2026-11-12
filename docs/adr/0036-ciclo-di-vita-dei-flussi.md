# ADR 0036 — Ciclo di vita dei flussi: stati e versioni nel domain, schema di 0008 invariato

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.1.2 (Task T1.1.2.1), R1.1.3 (Task T1.1.3.1), R1.1.4 (Task T1.1.4.1), R1.1.6 (Task T1.1.6.1)

## Contesto

Dopo la creazione (R1.1.1, ADR 0031) un flusso deve poter essere modificato conservando le versioni
precedenti e confrontandole (R1.1.3), avviato, messo in pausa e ripreso (R1.1.4), archiviato in modo
definitivo (R1.1.6). Due flussi non archiviati dello stesso conto non condividono asset, alla creazione come
alla modifica (R1.1.2). La migrazione 0008 ha già `flows.status`, aggiornabile dal ruolo applicativo, e
`flow_versions`, solo in inserimento. I cicli (F1.2) e le posizioni attribuite al flusso (F1.6) non esistono
ancora.

## Decisione

- **Transizioni nel domain.** `FlowCommand` (avvia, pausa, riprendi) dichiara lo stato da cui parte e quello
  a cui porta; `Flow.after(command)` rifiuta ogni altro stato con `FlowCommandNotAllowedError` "comando X non
  ammesso per un flusso Y" (409). `Flow.archived()` vale solo da fermo (`ArchiveOnlyStoppedError`, 409); un
  flusso archiviato non accetta comandi né modifiche (`ArchivedFlowNotModifiableError`, 409). Lo stop (R1.1.5)
  arriverà come transizione propria, perché chiude le posizioni.
- **Versioni.** `Flow.reconfigured(configuration)` assegna la versione successiva a quella in vigore; il
  repository la inserisce in `flow_versions` (`add_version`), senza mai toccare le precedenti. La versione in
  vigore resta la più alta, come già in `list`.
- **Modifica parziale.** `ModifyFlowCommand` porta solo le parti che cambiano; le altre restano quelle della
  versione in vigore. Valgono le regole della creazione, verificate dagli stessi contesti: un modello nuovo
  senza parametri prende i propri predefiniti; un modello non toccato non si riverifica. Il conto non si
  cambia (`AccountNotChangeableError`, 422). Il capitale allocato non si modifica qui: ha la sua variazione
  registrata (R1.1.7). Il controllo dell'archiviazione precede ogni altro, così la risposta non dipende dalla
  modifica chiesta.
- **Conflitto sugli asset** come regola del domain (`require_assets_free`): si confrontano i flussi non
  archiviati dello stesso conto, escluso quello che si modifica; il rifiuto nomina il flusso e gli asset in
  comune (`AssetsAssignedToOtherFlowError`, 409). Asset e negoziabilità si ricontrollano solo se gli asset
  cambiano.
- **Confronto** come funzione del domain (`differences`): per ogni parte della configurazione, nell'ordine,
  il valore prima e dopo come testo; le parti uguali non compaiono.
- **Elenco**: i flussi in uso escludono gli archiviati, che si leggono a parte (`archived=True`).
- **Nessuna migrazione**: lo schema di 0008 basta. Così il lavoro non dipende dalla migrazione 0009 di
  Telegram, in sviluppo in parallelo.
- **API**: `PATCH /flows/{id}`, `GET /flows/{id}/versions/{n}`, `GET /flows/{id}/versions/{a}/differences/{b}`,
  `POST /flows/{id}/start|pause|resume`, `POST /flows/{id}/archive`, `GET /flows?archived=true`.

## Alternative scartate

- **Una tabella di macchina a stati in configurazione**: le transizioni sono regole del requisito e cambiano
  con il codice che le applica.
- **Sostituzione dell'intera configurazione a ogni modifica**: obbliga il client a rimandare tutto e rende
  ambiguo che cosa l'utente ha cambiato.
- **Migrazione 0010 su 0008**: due teste Alembic in parallelo con 0009, da fondere poi; inutile, lo schema
  basta.
- **Codice 422 per conflitti di stato**: 409 dice che la richiesta è valida ma lo stato attuale non la
  ammette, come per il nome già usato.

## Conseguenze

- Restano `@wip` gli scenari che chiedono i cicli (primo ciclo all'avvio, ciclo in corso, cicli registrati) o
  le posizioni attribuite al flusso (pausa e ripresa con posizione, asset con posizione aperta).
- Il ciclo (F1.2) leggerà la versione in vigore al suo inizio: una modifica vale dal ciclo successivo.
