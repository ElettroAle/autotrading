# ADR elenco-dei-conti-e-pagina-del-conto — Elenco compatto dei conti e pagina del conto con schede

- Stato: proposta (18 novembre 2026)
- Requisiti: Bug 616, Task 617; R2.3.1, R2.2.1, R3.3.2, R3.2.3, R6.2.3
- Collegate: `.claude/rules/tech-dashboard.md`; ADR reusable components (`ViewTabs`, `DangerZone`, `CommandButton`,
  `ConfirmationDialog`, `details-list`); ADR scomposizione-del-saldo-nel-riquadro-del-conto,
  movimenti-non-spiegati-nel-riquadro-del-conto, pagina-avvisi-nella-dashboard
- Verifica: prova

## Contesto e problema

Nella pagina Conti ogni conto è un riquadro con saldo e scomposizione, l'intera riconciliazione, i movimenti non
spiegati e cinque comandi: su telefono un solo conto occupa più schermate e l'elenco non si consulta (Bug 616).

## Fattori decisionali

- Proprietario (18/11/2026): elenco compatto più pagina del conto con schede, come i portali cloud (Azure, AWS) e come
  la pagina del flusso (R6.4.3).
- `tech-dashboard.md` §Pagine di impostazioni: prima ciò che si usa spesso, dettagli solo quando servono, stato
  visibile con icona e testo, mai solo col colore.
- Componenti condivisi esistenti, nessuna copia: `ViewTabs`, `DangerZone`, `CommandButton`, `ConfirmationDialog`.
- Nessuna logica nuova nell'API: la dashboard riusa le letture esistenti (ADR 0116).

## Decisione

- **Pagina Conti** (`/accounts`): un elemento compatto per conto, collegamento alla sua pagina, con nome, badge della
  rete, stato della riconciliazione (icona e testo), saldo e capitale libero. Le azioni (Sostituisci le credenziali,
  Rimuovi) stanno in un menu «Azioni» dell'elemento, che apre gli stessi form e conferme di oggi. Registrazione di un
  conto e Zona di emergenza restano nella pagina (R3.2.3).
- **Pagina del conto** (`/accounts/:accountId`, rotte figlie come la pagina del flusso), con intestazione (nome,
  rete, stato) e `BackButton` verso Conti, e schede `ViewTabs`:
  - **Panoramica** (predefinita): saldo con risultato aperto, capitale allocato, valore e risultato dei flussi,
    capitale libero, campi pubblici (indirizzo);
  - **Riconciliazione**: ultimo confronto, saldo atteso e letto, scostamento, soglia con «Modifica la soglia»,
    movimenti non spiegati, link agli avvisi del conto (`/alerts?resource_id=<id>&state=all`);
  - **Capitale**: lo storico del capitale di oggi (la rotta `/accounts/:accountId/capital` diventa la scheda);
  - **Impostazioni**: sostituzione delle credenziali e rimozione nella `DangerZone`.
- Le rotte attuali restano raggiungibili: `/accounts/:accountId/alarms` continua a reindirizzare agli avvisi;
  i link delle notifiche e degli altri punti che portano a un conto puntano alla sua pagina.
- I componenti di oggi (`detail`, `reconciliation-status`, `flows-value`, `unattributable-movements`,
  `deviation-threshold-form`, `replace-credentials-form`, `remove-account`) si spostano nelle schede senza cambiare
  comportamento; il riquadro lungo `account-card` sparisce.

## Alternative scartate

- Riquadro con sezioni a scomparsa: scartata dal proprietario, la pagina resta lunga appena si apre una sezione.

## Conseguenze

- La prova di architettura verifica che l'elemento dell'elenco mostri solo i campi detti e che la pagina del conto
  usi `ViewTabs` con le quattro schede, `DangerZone` per la rimozione e `BackButton`.
- I passi degli scenari che leggono la riconciliazione o il capitale dalla pagina Conti aprono la scheda del conto.
