# ADR piano-di-uscita-nella-dashboard — Piano di uscita tra le posizioni aperte e nel dettaglio del ciclo

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.1 (454), Task T3.1.1.2 (472); R3.1.4 (457) per la stessa decisione mostrata
- Collegate: ADR piano-di-uscita-nella-decisione-dell-agente, ADR formato-dei-prezzi-condiviso, ADR
  tabella-condivisa-senza-sforamento-e-con-filtri, ADR liste-etichetta-valore-che-vanno-a-capo

## Contesto e problema

La dashboard mostra le posizioni aperte (`features/flow-positions`) e il dettaglio del ciclo (`features/cycles`,
`step-document.tsx`) senza piano di uscita. R3.1.1 chiede obiettivo, stop e invalidazione tra le posizioni aperte e
obiettivo e stop nella decisione del dettaglio del ciclo.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile (schede `ViewTabs`, tabella condivisa, riepilogo, grafici di `src/components/charts`, formato dei prezzi condiviso), nessun duplicato per pagina.
- `.claude/rules/tech-dashboard.md`: dati solo dall'API attraverso il client OpenAPI generato.

## Opzioni considerate

1. Le posizioni aperte aggiungono le colonne Obiettivo e Stop (prezzi con il formato condiviso, «—» se assenti) alla
   tabella condivisa e l'invalidazione come riga di dettaglio della posizione (testo che va a capo); sul telefono le
   colonne seguono le priorità della tabella condivisa. Nel dettaglio del ciclo la decisione mostra obiettivo, stop,
   invalidazione (e la confidenza di R3.1.4) con la lista etichetta-valore condivisa. Client OpenAPI rigenerato.
2. Un pannello dedicato al piano: scartato, duplica tabella e lista.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.1.1 della dashboard, unit test dei componenti).

### Conseguenze

- Nessun componente nuovo: tabella e lista condivise crescono di campi.
