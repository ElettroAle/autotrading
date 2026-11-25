# ADR perdita-giornaliera-dalla-ripresa-delle-aperture — La perdita giornaliera del flusso riparte dalla ripresa delle aperture

- Stato: accettata (25 novembre 2026)
- Requisiti: Bug 775 (Task 776), R3.2.2 (459)
- Sostituisce: ADR perdita-massima-sui-valori-di-equity-registrati (proposta)
- Collegate: ADR 0040 (controllo del rischio), ADR 0120 (l'equity di ogni ciclo si registra);
  `.claude/rules/context-flows.md`
- Verifica: prova

## Contesto e problema

La ripresa delle aperture dopo una perdita massima fa ripartire il picco, ma il riferimento della perdita giornaliera
resta il valore delle 00:00 UTC. Dopo una sospensione per perdita giornaliera e la ripresa confermata dall'utente, il
ciclo successivo misura la stessa perdita, ancora oltre la soglia, e sospende di nuovo le aperture: la ripresa non ha
effetto fino a mezzanotte.

## Fattori decisionali

- Decisione del proprietario sul Bug 775 (25 novembre 2026): dopo la ripresa la perdita giornaliera si misura dal
  valore al momento della ripresa, fino alle 00:00 UTC successive; solo il comando di ripresa azzera i riferimenti,
  fermare e riavviare il flusso non li tocca.
- R3.2.2: perdita giornaliera rispetto alle 00:00 UTC, picco dall'avvio o dall'ultima ripresa.
- `CLAUDE.md`: regole di business nel domain; nessuna duplicazione.

## Decisione

Resta tutto ciò che l'ADR sostituita decideva, salvo quanto segue.

- Il riferimento giornaliero è l'ultima equity registrata entro il più tardo tra le 00:00 UTC di oggi e l'ultima
  ripresa delle aperture (la prima registrata da quell'istante se il flusso non ne ha prima), portata al capitale di
  oggi come prima. Il giorno dopo la ripresa torna il valore delle 00:00 UTC.
- La regola sta nel domain, accanto a quella del picco: `OpeningsStatus` dice da quale istante conta la perdita
  giornaliera (il più tardo tra l'inizio del giorno e la ripresa) come dice da quale conta il picco.
  `GuardFlowLossUseCase` passa quell'istante alla porta dei riferimenti, che non cambia contratto.
- La ripresa «il giorno dopo» cade alle 00:00 UTC: per lei il riferimento non cambia.
- Nessuna migrazione: l'istante dell'ultima ripresa è già salvato sul flusso. Fermare e riavviare il flusso non cambia
  la sospensione né i riferimenti.

## Alternative scartate

- **Perdita giornaliera ignorata fino alle 00:00 UTC dopo una ripresa**: lascia il flusso senza limite giornaliero per
  il resto del giorno.
- **Riavvio del flusso come ripresa**: escluso dal proprietario.

## Conseguenze

- Dopo una ripresa il flusso può perdere fino alla soglia giornaliera di nuovo, misurata dal valore della ripresa,
  prima di una nuova sospensione.
- L'ADR perdita-massima-sui-valori-di-equity-registrati diventa superata.
