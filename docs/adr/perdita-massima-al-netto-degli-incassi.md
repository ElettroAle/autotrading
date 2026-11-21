# ADR perdita-massima-al-netto-degli-incassi — Un incasso non è una perdita per la perdita massima del flusso

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 688 (Task 694); R3.2.2, R3.4.1
- Collegate: ADR incasso-dei-profitti
- Verifica: prova

## Contesto e problema

Il valore del flusso è capitale allocato + PnL realizzato − commissioni + funding − profitti incassati (R1.6.1, R3.4.1).
`LossGuard.of` (`domain/flows/loss_guard.py`) misura la perdita dal valore a mezzanotte e dal picco, riportati al capitale
attuale da `at_capital`, che però non toglie i profitti incassati dopo la registrazione del riferimento: un incasso di 150
abbassa il valore di 150 e conta come perdita, contro R3.2.2 («aumenti, riduzioni e incassi non sono perdite»).

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): il riferimento toglie il profitto incassato dopo la sua
  registrazione; modifica solo nel dominio.
- `EquitySnapshot.cashed_profit` registra i profitti incassati fino alla fotografia; il flusso conosce quelli fino a ora.

## Decisione

`at_capital(snapshot, capital, cashed_profit)` diventa: valore registrato − capitale di allora + capitale di ora −
(profitti incassati ora − profitti incassati alla fotografia). `LossGuard.of` riceve i profitti incassati del flusso
(dallo stato già letto da `GuardFlowLossUseCase`) e li passa per il riferimento giornaliero e per il picco. Nessun altro
cambio.

## Alternative scartate

- Escludere dal conteggio il ciclo dell'incasso: la perdita tornerebbe al ciclo successivo.

## Conseguenze

- Un incasso non avvicina né supera la perdita giornaliera o dal picco; le perdite vere restano misurate come oggi.

## Prove

- Scenario in R3.2.2 (worker): flusso con picco 1150 che incassa 150, perdita dal picco 10%: nessuna sospensione.
- Unit test di `at_capital` e `LossGuard.of` con incassi prima e dopo la fotografia.
