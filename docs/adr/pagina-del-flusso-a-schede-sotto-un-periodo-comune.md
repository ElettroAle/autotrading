# ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune — Pagina del flusso a schede sotto un periodo comune

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.3 (421), Task T6.4.3.1 (422); Bug 439, Task 440
- Collegate: ADR viste-e-comandi-della-pagina-del-flusso (sostituita in parte per l'ordine e le viste), ADR
  schede-con-aspetto-e-ruolo-di-schede, ADR riepilogo-dei-risultati-nella-dashboard, ADR
  tabella-condivisa-senza-sforamento-e-con-filtri

## Contesto e problema

Il periodo sta a metà della pagina del flusso e vale solo per grafico e statistiche; le viste (posizioni, cicli)
sono pagine separate con filtri propri; l'elenco dei cicli recenti spinge il grafico in fondo. Il proprietario
chiede un solo filtro in cima che valga per tutte le schede, senza filtri nascosti che agiscono su altre viste, e
toglie i cicli recenti (16/11/2026).

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile (schede `ViewTabs`, tabella condivisa, riepilogo, grafici di `src/components/charts`), nessun duplicato per pagina.
- R6.4.3 e decisioni del proprietario (16/11/2026).
- Rotte esistenti `/flows/:flowId`, `/positions`, `/closed-positions`, `/cycles`, `/versions`, `/edit`.
- `.claude/rules/tech-dashboard.md`: React Router, stato dei filtri nell'indirizzo.

## Opzioni considerate

1. Una rotta di layout del flusso con intestazione (nome, stato, comandi di stato, avviso), periodo e schede
   Panoramica, Posizioni chiuse, Cicli come rotte figlie (`/flows/:flowId`, `/closed-positions`, `/cycles`); il
   periodo (e l'intervallo) sta nei parametri dell'indirizzo condivisi dalle figlie. La Panoramica contiene
   riepilogo, equity curve, statistiche e posizioni aperte attuali (la rotta `/positions` porta alla Panoramica).
   Configurazione, versioni, modifica, duplica ed esporta sotto il comando Configurazione (rotte `/versions` e
   `/edit` fuori dal layout del periodo). L'elenco dei cicli recenti si toglie.
2. Una sola pagina con contenuti nascosti: scartata, perde gli indirizzi delle viste e il tasto Indietro.

## Esito della decisione

Opzione 1. Le schede sono il componente condiviso `ViewTabs` nella rotta di layout, quindi restano visibili sopra ogni
scheda; la barra parte dalla prima scheda intera e il suo sfondo copre tutta la larghezza che scorre (Bug 439).

Verifica: prova (scenari di R6.4.3, prova di layout della barra a 360 e 1280 px, unit test dei componenti, scenari esistenti di E2 aggiornati ai nuovi titoli e
alle schede).

### Conseguenze

- Il periodo è uno solo e si vede sempre sopra ciò che filtra.
