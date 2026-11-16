# ADR limite-di-frequenza-dell-exchange-come-indisponibilita — Limite di frequenza dell'exchange come indisponibilità

- Stato: accettata (16 novembre 2026, approvata dal proprietario)
- Requisiti: Bug 443, Task 444; R1.2.3 (fallimento del ciclo col messaggio originale), R1.2.4 (errore permanente)
- Collegate: `.claude/rules/tech-hyperliquid.md`, ADR 0027 (l'errore dichiara la propria risposta)

## Contesto e problema

L'SDK Hyperliquid solleva `ClientError` per ogni risposta 4xx, compreso 429 (troppe richieste). L'adapter traduce ogni
`ClientError` in credenziali rifiutate (`ExchangeRejectedCredentialsError`, poi `FlowCredentialsRefusedError`, errore
permanente che mette in pausa i flussi del conto) e, negli ordini, in `ExchangeRejectedOrderError`. Un limite di
frequenza passeggero diventa così «credenziali del conto non valide» (dev, 16/11/2026). Inoltre il fallimento del ciclo
conserva solo «credenziali del conto non valide: <conto>», senza il motivo dato dall'exchange.

## Fattori decisionali

- R1.2.4: solo un errore che non passa da solo mette in pausa i flussi.
- R1.2.3: il fallimento del ciclo porta il messaggio originale dell'errore.
- Le eccezioni della libreria si traducono solo nell'adapter, nell'errore del contratto della porta.
- I segreti non escono mai dall'adapter (messaggi mascherati come oggi).

## Opzioni considerate

1. Nell'adapter Hyperliquid un `ClientError` con `status_code` 429 si traduce nell'errore di indisponibilità del
   contratto (`ExchangeUnavailableError` nelle letture, `OrderExchangeUnavailableError` negli ordini), come
   `ServerError`.
2. Ritentare il 429 dentro l'adapter: scartato, il ciclo successivo è già il nuovo tentativo e un'attesa dentro il
   ciclo ne allunga la durata.

## Esito della decisione

Opzione 1. Il motivo dell'exchange nel fallimento del ciclo resta fuori: il messaggio di R1.2.4 è fissato dai suoi
criteri di accettazione e cambiarlo è una decisione del proprietario, separata da questo Bug.

Verifica: prova (unit test dell'adapter: 429 come indisponibilità in lettura e negli ordini, altro 4xx ancora
rifiuto).

### Conseguenze

- Un limite di frequenza salta il ciclo senza mettere in pausa i flussi.
