# ADR rendimento-composto-tra-le-variazioni-di-capitale — Rendimento composto tra le variazioni di capitale

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.4.3 (466), Task T3.4.3.1 (490)
- Collegate: ADR 0127 (riepilogo con capitale iniziale), ADR incasso-dei-profitti, ADR
  capitale-libero-al-netto-del-valore-dei-flussi, ADR cicli-falliti-sull-equity-curve, ADR 0121 (grafici con Recharts)

## Contesto e problema

Oggi il rendimento è (valore complessivo − capitale allocato attuale) / capitale allocato attuale (`FlowReturn`), quindi
un aumento, una riduzione o un incasso lo cambiano nel momento in cui avvengono. R3.4.3 vuole il rendimento composto dei
periodi tra le variazioni, uguale ovunque compaia, e le variazioni segnate sull'equity curve.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): componenti riusabili, nessun duplicato; il grafico condiviso riceve gli
  eventi dalla funzionalità (ADR cicli-falliti-sull-equity-curve).
- CLAUDE.md e decisione del proprietario sui calcoli: un solo calcolo canonico, nel domain, usato da stato, riepilogo,
  classifica, statistiche e contesto dell'agente.

## Opzioni considerate

1. `FlowReturn` composto: riceve le variazioni di capitale del flusso con il valore del flusso prima di ciascuna
   (registrato dall'ADR incasso-dei-profitti anche per aumento e riduzione) e il valore attuale. Il periodo i va dal
   valore dopo la variazione i (valore prima ± importo) al valore prima della variazione successiva; l'ultimo periodo
   finisce al valore attuale e il primo parte dal capitale allocato all'avvio. Il rendimento è il prodotto dei
   rapporti dei periodi, meno 1.
2. Rendimento sul capitale netto investito (Modified Dietz): scartata, perché R3.4.3 prescrive il composto dei periodi.

## Esito della decisione

Opzione 1.

- Le variazioni registrate prima di questa ADR non hanno il valore prima: la catena parte dal capitale allocato dopo
  l'ultima di esse, così un flusso senza variazioni nuove ha lo stesso rendimento di oggi.
- Il PnL in valuta è il PnL realizzato netto più il non realizzato, senza togliere gli incassi.
- Ogni lettore del rendimento (stato e riepilogo R2.2.2, classifica R2.4.2, statistiche R2.2.6, contesto del ciclo
  RF-13.04) riceve le variazioni dalla porta del flusso e usa `FlowReturn`; non resta nessun altro calcolo del
  rendimento.
- Equity curve: le variazioni del periodo arrivano dalla stessa API dello storico (ADR
  storico-delle-variazioni-di-capitale) e il grafico condiviso le disegna come eventi con etichetta («incasso, 100
  USDC»), distinti dal segno dei cicli falliti.

Verifica: prova (scenari di R3.4.3; unit test di `FlowReturn` sugli esempi degli scenari; un test che nessun altro
modulo calcola il rendimento dal capitale allocato).

### Conseguenze

- Il rendimento non dipende più dal capitale allocato attuale: confronti e classifica misurano solo l'agente.
