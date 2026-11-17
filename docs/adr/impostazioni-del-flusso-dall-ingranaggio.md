# ADR impostazioni-del-flusso-dall-ingranaggio — Pagina Impostazioni del flusso aperta dall'ingranaggio

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 560, Task 561; R2.3.3, R3.2.3, R6.4.3
- Collegate: ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune, ADR zona-di-emergenza-in-fondo-alla-pagina, ADR
  assegnazione-della-bozza-nel-form-di-configurazione, ADR voce-generale-con-la-zona-pericolosa,
  `.claude/rules/tech-dashboard.md` §Pagine di impostazioni
- Verifica: prova

## Contesto e problema

La pagina del flusso mescola lettura, comandi d'esercizio e impostazioni: il collegamento «Configurazione» sta sotto i
comandi (`features/flows/components/flow-view.tsx`), la chiusura di emergenza del flusso in fondo alla panoramica
(`app/routes/app/flow.tsx`, `FlowDangerZone`) e Archivia tra i comandi (`flow-commands.tsx`). Configurazione, versioni,
Duplica ed Esporta stanno nella rotta `/flows/:flowId/versions`. Il proprietario (17/11/2026): ingranaggio in alto a
destra per le impostazioni, non una scheda (che mischierebbe lettura e scrittura); nella pagina impostazioni
configurazione, gestione e zona pericolosa.

## Fattori decisionali

- Decisione del proprietario (17/11/2026), Bug 560: «Config + gestione + zona».
- La pagina del flusso resta lettura e comandi d'esercizio (Avvia, Pausa, Riprendi, Ferma, Esegui ora).
- Componenti condivisi: `DangerZone`, `EmergencyClosingCommand`, `ConfirmationDialog`, `Icon`, `CommandButton`.

## Decisione

- La rotta `/flows/:flowId/versions` diventa `/flows/:flowId/settings` (`paths.flowSettings`), titolo «Impostazioni del
  flusso»: in ordine la configurazione con Modifica, Duplica ed Esporta (`FlowConfiguration`), le versioni
  (`FlowVersions`) e in fondo `<DangerZone>` con la chiusura di emergenza del flusso (non per una bozza) e Archivia (per
  un flusso fermo o una bozza, con la conferma di oggi). Il vecchio indirizzo `/versions` reindirizza al nuovo.
- Testata del flusso: un ingranaggio (`Icon` «settings», `aria-label` «Impostazioni del flusso») in alto a destra
  della sezione del flusso apre la pagina; spariscono il collegamento «Configurazione», `FlowDangerZone` da `flow.tsx`
  e Archivia da `FlowCommands`.
- Scenari che citano la vecchia posizione (R2.3.3 configurazione, R3.2.3 zona del flusso, Archivia) si riallineano.
- Prove: unit test di testata e pagina; prova di architettura che la chiusura di emergenza del flusso e Archivia
  stanno solo nella pagina delle impostazioni.

## Alternative scartate

- Scheda «Impostazioni» tra le schede del flusso: mescola lettura e scrittura (proprietario).

## Conseguenze

- Le azioni distruttive del flusso stanno tutte in una pagina, in fondo.
