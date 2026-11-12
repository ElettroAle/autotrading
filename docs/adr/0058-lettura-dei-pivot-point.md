# ADR 0058 — Lettura dei pivot point nel ciclo

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.3.4 (Task T1.3.4.1)

## Contesto

R1.3.4 chiede i pivot classici della giornata UTC precedente (PP, R1, R2, S1, S2), la posizione del prezzo
rispetto al PP e la distanza percentuale dal supporto e dalla resistenza più vicini; sopra R2 e sotto S2 il
contesto dichiara che non c'è un livello più vicino. Formula e lettura del prezzo esistono nel domain
(`PivotLevels`, ADR 0032). Mancano la giornata precedente, il prezzo corrente e il lettore nel ciclo.

## Decisione

- **Dati** dalla stessa `MarketDataPort` degli indicatori (ADR 0057):
  - `previous_day`: la candela giornaliera di Hyperliquid che apre alla mezzanotte UTC di ieri. Se manca, la
    fonte è assente nel ciclo.
  - Il prezzo corrente è il mark price di `snapshot`, lo stesso prezzo che riceve la fonte indicatori.
- **Lettore** `ReadPivotsUseCase`, con questi valori:
  - i cinque livelli e `prezzo`;
  - `posizione_rispetto_al_pp`, che vale `sopra`, `sotto` o `sul`;
  - `resistenza_vicina` e `distanza_resistenza_percentuale`;
  - `supporto_vicino` e `distanza_supporto_percentuale`.

  La distanza è in percentuale del prezzo, con due decimali. Senza livello su un lato restano solo
  `resistenza_vicina` = "nessuna resistenza sopra il prezzo" o `supporto_vicino` = "nessun supporto sotto il
  prezzo".
- **Riferimento del dato**: l'istante della lettura, perché la posizione dipende dal prezzo corrente.

## Alternative scartate

- **Giornata precedente ricavata da candele orarie**: stesso risultato con 24 volte i dati; la candela giornaliera
  dell'exchange è già allineata alla giornata UTC.
- **Mid price come prezzo corrente**: il mark price è il prezzo su cui l'exchange valuta posizioni e
  liquidazioni; usare lo stesso prezzo in tutte le fonti evita due "prezzi correnti" diversi nel contesto.

## Conseguenze

- Una chiamata di candela giornaliera e una dei valori correnti per asset e ciclo.
- Un prezzo uguale a un livello lo conta come supporto (ADR 0032), con distanza 0,00%.
