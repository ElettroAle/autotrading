# ADR totali-dello-storico-sul-risultato-filtrato — Totali di PnL e commissioni su tutto il risultato filtrato

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 569, Task 570 e 571; F2.5 (storico)
- Collegate: ADR dello storico (F2.5), `.claude/rules/context-flows.md`
- Verifica: prova

## Contesto e problema

Lo Storico (`GET /history/closed-positions` e `/history/orders`, `adapters/inbound/api/history.py:193-219`) è
paginato a 50 righe con cursore e filtri (periodo, flusso, conto, asset, versione). Non c'è nessun totale; sommare
in pagina darebbe solo la parte caricata.

## Fattori decisionali

- Bug 569: totali di PnL e commissioni coerenti con i filtri, non con la pagina.
- Multi-tenancy: la somma gira nella stessa query filtrata e con RLS.
- Importi in `Decimal`, mai `float`.

## Decisione

- Application: la porta della lettura dello storico delle posizioni chiuse aggiunge i totali (`pnl`, `fees`) calcolati
  con gli stessi filtri, ignorando il cursore; `QueryClosedPositionHistoryUseCase` li restituisce con la pagina. Per
  gli ordini, il totale delle commissioni se le righe degli ordini le portano.
- Adapter SQLAlchemy: `SUM` sulla stessa selezione filtrata. API: campo `totals` nella risposta (stringhe decimali
  come gli altri importi), solo alla prima pagina (senza `after`) per non ricalcolarlo a ogni «Carica altri».
- Dashboard: riga dei totali sopra la tabella della scheda («Totale PnL», «Totale commissioni», con il colore del
  segno), aggiornata al cambio dei filtri.
- Prove: scenari dello storico con totali su più pagine e filtri; unit test dell'adapter e del componente.

## Alternative scartate

- Somma nella dashboard delle righe caricate: incoerente con i filtri.

## Conseguenze

- Una query di somma in più alla prima pagina.
