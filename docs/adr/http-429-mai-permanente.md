# ADR http-429-mai-permanente — Un HTTP 429 non è mai un errore permanente

- Stato: accettata (16 novembre 2026, decisione del proprietario)
- Requisiti: Bug 445, Task 446; R1.2.4 (pausa per errori permanenti)
- Collegate: ADR 0039 e ADR 0101, superate solo nella parte «429 con quota esaurita = credito esaurito»; ADR
  limite-di-frequenza-dell-exchange-come-indisponibilita (Bug 443); ADR 0027

## Contesto e problema

Un errore permanente mette in pausa i flussi (R1.2.4). L'adapter litellm traduce un 429 con «insufficient_quota» o
«exceeded your current quota» in `ModelCreditExhaustedError`, permanente (ADR 0039, ADR 0101, `tech-litellm.md`);
l'adapter hyperliquid traduceva ogni 4xx, 429 compreso, in credenziali rifiutate (Bug 443).

## Fattori decisionali

- Decisione del proprietario (16/11/2026): «429 non è mai permanente, non dipende dagli adapter».
- La traduzione dalle eccezioni della libreria all'errore del contratto avviene solo nell'adapter
  (`layer-adapters.md`); la decisione sulla pausa resta unica, sul `permanent` dell'errore (ADR 0027).

## Opzioni considerate

1. Regola di tutti gli adapter in uscita in `layer-adapters.md`: un HTTP 429 di qualunque sistema si traduce sempre
   nell'errore temporaneo del contratto della porta, mai in uno permanente. L'adapter litellm traduce ogni 429 in
   `ModelUnavailableError`; il credito esaurito resta permanente solo con 402. `tech-litellm.md` si allinea.
2. Lasciare a ogni adapter la scelta sul 429: scartata dal proprietario.

## Esito della decisione

Opzione 1.

Verifica: prova (unit test dell'adapter litellm: un 429 con quota esaurita è `ModelUnavailableError`, non permanente;
402 resta `ModelCreditExhaustedError`).

### Conseguenze

- Una quota esaurita segnalata con 429 fa fallire i cicli senza mettere in pausa i flussi finché il fornitore la
  ripristina.
