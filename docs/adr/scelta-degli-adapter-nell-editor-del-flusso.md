# ADR scelta-degli-adapter-nell-editor-del-flusso — Adapter delle fonti scelti nell'editor del flusso

- Stato: proposta (19 novembre 2026)
- Requisiti: US 310 R4.1.1, Task 313; dipende dal Task 311
- Collegate: ADR fonti-con-adapter-dichiarati, ADR 0131 (editor guidato dai cataloghi dell'API), ADR
  icone-con-lucide-react-e-comandi-condivisi; `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

Nell'editor del flusso `SourceFields` (`features/flow-editor/components/source-fields.tsx`) mostra per ogni fonte una
casella «attiva», il peso e i parametri presi dal catalogo. Con R4.1.1 una fonte attiva sceglie uno o più adapter,
ciascuno col suo peso e i suoi parametri, e un adapter dichiara se richiede configurazione.

## Fattori decisionali

- L'editor si genera dai cataloghi dell'API, nessuna regola nella dashboard (ADR 0131): adapter, parametri, campi e
  motivi arrivano da `GET /sources`.
- Regole UX delle pagine con moduli (`tech-dashboard.md`): componenti condivisi, etichette esplicite, errori accanto al
  campo, utilizzabile a 360 px.
- Gli adapter che richiedono configurazione diventano attivabili solo con le credenziali (R4.1.2): l'editor deve
  già saper mostrare un adapter non attivabile col motivo.

## Decisione

- Per ogni fonte del catalogo: nome, descrizione e la casella «attiva» come oggi. Con la fonte attiva compare l'elenco
  dei suoi adapter, ognuno con una casella, nome e descrizione; una fonte con un solo adapter lo ha già scelto
  quando la si attiva. Ogni adapter scelto mostra sotto di sé peso (1-10) e parametri generati dalla dichiarazione,
  con le etichette «Peso di <fonte> · <adapter>».
- Un adapter senza campi di configurazione mostra «nessuna configurazione necessaria»; un adapter che l'API dichiara
  non attivabile ha la casella disabilitata e il motivo dell'API accanto (testo, non solo colore).
- Il rifiuto «scegli almeno un adapter della fonte <fonte>» arriva dall'API e si mostra sul gruppo della fonte.
- Valori del modulo: `sources.<fonte>.adapters.<adapter>.{active, weight, parameters}`; `sourcesOf` e la mappatura
  di modifica in `utils/flow-form.ts` producono e leggono il modello nuovo; cronologia e dettagli del flusso
  (`configuration-rows.ts`, `flow-details.tsx`) mostrano «fonte · adapter (peso N)».
- Layout: adapter in colonna sotto la fonte, campi di peso e parametri che vanno a capo; nessuno scorrimento
  orizzontale a 360 px.
- Scenari R4.1.1 della dashboard con Playwright sul finto MSW.

## Alternative scartate

- Una riga per coppia fonte-adapter senza raggruppamento: la fonte e il rifiuto «almeno un adapter» perdono il loro
  posto.

## Conseguenze

- La sezione Fonti di Impostazioni › Chiavi (R4.1.2) riusa nome e descrizione dell'adapter dallo stesso catalogo.
