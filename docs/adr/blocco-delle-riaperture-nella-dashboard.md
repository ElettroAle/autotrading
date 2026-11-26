# ADR blocco-delle-riaperture-nella-dashboard — Blocco delle riaperture nella dashboard

- Stato: accettata (26 novembre 2026)
- Requisiti: US 754 R5.5.2 (Task 757)
- Collegate: ADR 0116, ADR 0131, ADR perdita-massima-nella-dashboard, ADR limite-di-perdite-consecutive-del-flusso,
  ADR controllo-delle-riaperture-dopo-perdite-consecutive; `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.5.2 chiede i quattro campi del limite nel modulo del flusso, con i motivi di rifiuto dell'API, e i blocchi in corso
nella pagina del flusso.

## Fattori decisionali

- Regole UI/UX del repository: campi della stessa cosa insieme, con ciò che ammettono scritto accanto.
- Nessuna logica di business nella dashboard (ADR 0116).
- La sospensione per perdita massima si mostra già nella pagina del flusso (ADR perdita-massima-nella-dashboard).

## Decisione

- Nel modulo del flusso «Perdite consecutive massime», «Finestra delle perdite (ore)», «Durata del blocco (minuti)» e
  la scelta «Ambito del conteggio» (asset, flusso) stanno nella sezione dei limiti di rischio, subito dopo le soglie
  della perdita massima, ciascuno con la riga di aiuto. Il motivo di un rifiuto dell'API compare sotto il campo.
- Nella pagina del flusso i blocchi in corso compaiono accanto alla sospensione delle aperture, con il testo che l'API
  restituisce.

## Alternative scartate

- **Blocchi in una scheda a parte**: un limite di rischio in vigore va visto dove si vede la sospensione.

## Conseguenze

- La dashboard mostra ciò che l'API restituisce.
