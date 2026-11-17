# ADR riquadro-dell-ultima-decisione-nella-panoramica — Riquadro dell'ultima decisione nella Panoramica del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.4 (Task 523)
- Collegate: ADR decisioni-del-ciclo-registrate-per-asset, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune, ADR
  liste-etichetta-valore-che-vanno-a-capo, ADR icone-condivise-di-azioni-e-direzioni (R6.5.3, in parallelo), ADR 0116

## Contesto e problema

La Panoramica del flusso mostra riepilogo, equity curve, statistiche e posizioni aperte attuali. Serve un riquadro con
l'ultima decisione dell'agente, indipendente dal periodo scelto, con il collegamento al dettaglio del ciclo.

## Fattori decisionali

- Direttiva del proprietario (16/11/2026): regole architetturali e componenti riusabili.
  - Lista etichetta-valore condivisa: `DETAILS_GRID` e `DETAIL_VALUE` di `src/components/ui/details-list.ts`.
  - Istante con `src/utils/format-instant.ts`.
  - Rotta del ciclo dai `paths` esistenti.
  - Azione e direzione con `ActionLabel` e `DirectionLabel` di R6.5.3.
- `.claude/rules/tech-dashboard.md`: una funzionalità non importa un'altra; la pagina compone in `src/app`.
- R6.5.4: il riquadro dice di essere indipendente dal periodo; senza cicli conclusi dice «nessuna decisione ancora».

## Opzioni considerate

1. **Funzionalità `features/last-decision`.**
   - `api/get-last-decision.ts`, una query TanStack su `GET /flows/{flow_id}/decisions/latest`, con risposta
     validata da Zod. La chiave non comprende il periodo.
   - `components/last-decision.tsx`: titolo «Ultima decisione», sottotitolo «indipendente dal periodo» e istante del
     ciclo come collegamento al dettaglio. Per ogni asset, in lista etichetta-valore: asset, azione, direzione se
     c'è, confidenza (o «non disponibile») e ragionamento accorciato.
   - Il ragionamento si accorcia a 160 caratteri sul confine di parola con «…», con un'utilità condivisa
     `src/utils/shorten-text.ts`, che R6.5.5 riusa. Il testo intero sta nel dettaglio del ciclo.
   - La rotta della Panoramica compone il riquadro sotto il riepilogo.
   - Se R6.5.3 è già integrato si usano `ActionLabel` e `DirectionLabel`. Altrimenti il testo semplice, e il ramo che
     integra per secondo allinea.
2. **Riquadro dentro `flow-statistics`**: scartata, perché le statistiche seguono il periodo e il riquadro no.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test del riquadro: decisione mostrata, confidenza assente, stato vuoto, collegamento.
- Unit test di `shorten-text`.
- Scenari Playwright di R6.5.4 con i finti MSW, che ricevono la rotta nuova.

### Conseguenze

- Una richiesta in più alla Panoramica, che non cambia con il periodo e resta in cache.
