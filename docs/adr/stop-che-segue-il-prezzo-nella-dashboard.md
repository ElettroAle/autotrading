# ADR stop-che-segue-il-prezzo-nella-dashboard — Stop che segue il prezzo nella dashboard

- Stato: accettata (26 novembre 2026)
- Requisiti: US 749 R5.5.1 (Task 753)
- Collegate: ADR 0116 (dashboard secondo bulletproof-react), ADR 0131 (editor della configurazione guidato dai campi),
  ADR impostazioni-dello-stop-che-segue-il-prezzo, ADR massimo-profitto-raggiunto-nello-stato-della-posizione;
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.5.1 chiede i campi delle impostazioni nel modulo del flusso con i motivi di rifiuto dell'API, e lo stop in vigore e
il massimo profitto raggiunto nella vista delle posizioni.

## Fattori decisionali

- Regole UI/UX del repository e decisione del proprietario: campi accanto a quelli che riguardano la stessa cosa, con
  ciò che ammettono scritto accanto.
- Nessuna logica di business nella dashboard (ADR 0116): i motivi di rifiuto vengono dall'API.

## Decisione

- Nel modulo del flusso i campi «Distanza dello stop che segue», «Attivazione», «Pareggio» (percentuali, vuoti
  ammessi) e la casella «Massimo profitto raggiunto nel contesto dell'agente» stanno nella sezione delle protezioni,
  subito dopo stop loss e take profit predefiniti, ciascuno con la riga di aiuto che dice che cosa ammette. Il motivo di
  un rifiuto dell'API compare sotto il campo; la dashboard non ripete le invarianti.
- Nella vista delle posizioni, «Stop», «Obiettivo» (dallo stato in vigore) e «Massimo profitto raggiunto», vuoto quando
  l'API non lo restituisce.

## Alternative scartate

- **Sezione separata per lo stop che segue**: separa impostazioni della stessa protezione.

## Conseguenze

- La dashboard mostra ciò che l'API restituisce, senza calcoli propri.
