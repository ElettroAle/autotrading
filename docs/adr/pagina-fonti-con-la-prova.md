# ADR pagina-fonti-con-la-prova — Pagina Fonti con la prova di ogni adapter

- Stato: proposta (19 novembre 2026)
- Requisiti: US 404 R6.3.1, Task 406; dipende dal Task 405
- Collegate: ADR prova-di-un-adapter-di-fonte-nel-worker, ADR 0131 (moduli dai cataloghi dell'API), ADR
  scelta-degli-adapter-nell-editor-del-flusso, ADR icone-con-lucide-react-e-comandi-condivisi;
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R6.3.1 vuole nella dashboard una pagina Fonti che elenca le fonti del catalogo e, per ciascuna, permette di scegliere
asset e parametri (con i predefiniti) e di premere Prova, mostrando esito, valori, istante dei dati e tempo di
risposta; parametri fuori dai limiti fermano la prova e il campo mostra il limite.

## Fattori decisionali

- bulletproof-react: nuova funzionalità, nessun import tra funzionalità; il catalogo si legge dall'API (ADR 0131).
- Regole UX: componenti condivisi, stato mai solo col colore, errori accanto al campo, utilizzabile a 360 px.

## Decisione

- Funzionalità `features/source-trials` con la sua lettura del catalogo `GET /sources` e la mutazione della prova; rotta
  `paths.sources` («/fonti») e voce «Fonti» nel gruppo principale della navigazione, dopo «Avvisi».
- Una scheda per fonte (nome, descrizione) con il modulo di prova: scelta dell'adapter (solo se più di uno, altrimenti
  l'unico è indicato per nome), asset solo per le fonti per asset, un campo numerico per ogni parametro dell'adapter
  con valore predefinito, `min` e `max` dal catalogo e schema zod generato dagli stessi limiti: un valore fuori limite
  non invia la richiesta e il campo dice «ammesso da X a Y». Un 422 dell'API si mostra sul campo come fallback.
- Pulsante «Prova» del componente condiviso dei comandi, disabilitato durante la prova.
- Esito sotto il modulo, in una regione `aria-live`: «riuscita» o «errore» con testo e icona; per la riuscita i valori
  letti (per asset se la fonte è per asset) in un elenco chiave-valore, istante dei dati in ora locale e tempo di
  risposta in millisecondi; per l'errore il motivo e «transitorio» o «permanente». L'ultimo esito resta finché non si
  riprova.
- Schede impilate a tutta larghezza; nessuno scorrimento orizzontale a 360 px; valori lunghi che vanno a capo.
- Scenari R6.3.1 della dashboard con Playwright sul finto MSW.

## Alternative scartate

- Prova dentro l'editor del flusso: R6.3.1 vuole una pagina a sé, senza toccare i flussi.

## Conseguenze

- Ogni adapter nuovo (E5) compare nella pagina senza codice della dashboard.
