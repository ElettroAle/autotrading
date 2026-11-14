# ADR 0143 — Valuta delle posizioni chiuse dallo stato del flusso già letto dalla pagina

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.5 (Bug: valuta mancante negli importi delle posizioni chiuse)
- Collegate: ADR 0128 (posizioni aperte e chiuse), ADR 0116; `GET /flows/{id}/state` (`currency`), `GET /flows/{id}/closed-positions`;
  `.claude/rules/tech-dashboard.md`

## Contesto e problema

La tabella delle posizioni chiuse mostra PnL e commissioni senza valuta, mentre lo scenario di R2.2.5 chiede «PnL +15 USDC».
La valuta del margine la conosce solo l'exchange: lo stato del flusso (`GET /flows/{id}/state`) la porta già, le posizioni
chiuse salvate nel database no. La pagina del flusso legge già lo stato per la tabella delle posizioni aperte.

## Decisione

- La tabella delle posizioni chiuse riceve la valuta dalla query TanStack dello stato del flusso già usata dalle posizioni
  aperte (stessa chiave, nessuna chiamata in più) e la aggiunge a PnL e commissioni con il componente condiviso degli importi.
- Se lo stato non è disponibile (exchange che non risponde), la tabella delle chiuse resta visibile con gli importi senza
  valuta: le chiuse non dipendono dall'exchange.
- Nessun cambio di API. Il passo Playwright di R2.2.5 verifica anche la valuta.

## Alternative scartate

- **`currency` nella risposta delle posizioni chiuse letta dall'exchange**: risposta autosufficiente, ma lo storico fallirebbe
  quando l'exchange non risponde.
- **Valuta salvata con ogni posizione chiusa**: storico autosufficiente, ma migrazione e dato duplicato per un valore che per
  conto non cambia.

## Conseguenze

- Con l'exchange irraggiungibile la valuta delle posizioni chiuse manca, come già il saldo nelle altre pagine.
