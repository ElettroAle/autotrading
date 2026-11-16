# ADR perdita-massima-nella-dashboard — Soglie, sospensione e ripresa delle aperture nella dashboard

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.2.2 (459), Task T3.2.2.2 (481)
- Collegate: ADR 0116 (dashboard secondo bulletproof-react), ADR 0131 (editor della configurazione guidato dai
  campi), ADR perdita-massima-sui-valori-di-equity-registrati, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune

## Contesto e problema

L'utente imposta soglie e modo di ripresa dal modulo del flusso, vede sul flusso che le aperture sono sospese e
perché, e conferma la ripresa.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove
  possibile, nessun duplicato per pagina.
- ADR 0116: la dashboard mostra ciò che l'API espone; lo stato della sospensione arriva dall'API.
- Bug 441: le parti nuove compaiono nelle righe del confronto delle versioni (`configuration-rows.ts`).

## Opzioni considerate

1. **Componenti esistenti estesi.**
   - Modulo (`features/flow-editor`): due campi percentuali facoltativi e la scelta della ripresa ("manuale",
     "il giorno dopo") con i campi condivisi di `src/components/ui/form`, nella sezione dei limiti di rischio;
     schema zod con gli stessi intervalli dell'API, l'errore dell'API resta la fonte del messaggio.
   - Avviso: l'intestazione del flusso, che già mostra il motivo della pausa automatica, mostra "aperture sospese:
     <motivo>" e il comando "Riprendi le aperture" in `features/flow-commands`, con il `ConfirmationDialog`
     condiviso; la mutazione chiama `POST /flows/{flow_id}/openings/resume` e invalida flusso ed elenco.
   - Elenco dei flussi: lo stesso testo dell'avviso accanto allo stato, nella tabella condivisa.
   - Versioni: righe "perdita giornaliera massima", "perdita massima dal picco", "ripresa delle aperture".
2. Una pagina a sé per la sospensione: scartata, l'avviso deve stare dove l'utente guarda il flusso.

## Esito della decisione

Opzione 1, con client OpenAPI rigenerato e mock di `src/testing/mocks` aggiornati.

Verifica: prova (scenario dashboard di R3.2.2 con playwright-bdd, unit test di modulo, avviso, comando ed elenco).

### Conseguenze

- Pausa automatica e sospensione delle aperture si leggono nello stesso punto della pagina del flusso.
