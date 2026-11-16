# ADR permanenza-decisa-dall-errore-base — La permanenza di un errore la decide l'errore base

- Stato: accettata (16 novembre 2026, decisione del proprietario)
- Requisiti: Bug 445, Task 446; R1.2.3, R1.2.4
- Collegate: ADR 0027 (superata solo nella parte «`permanent` dichiarato da ogni errore»); ADR 0039 e ADR 0101
  (superate solo nella parte «429 con quota esaurita = credito esaurito»); ADR
  limite-di-frequenza-dell-exchange-come-indisponibilita (superata: il caso speciale nell'adapter si toglie)

## Contesto e problema

Oggi `permanent` è un attributo di classe che ogni errore dichiara, falso se non lo ridefinisce; gli adapter scelgono
l'errore permanente o temporaneo catturando famiglie intere di eccezioni della libreria. Così un 429 di Hyperliquid è
diventato «credenziali del conto non valide», permanente, con la pausa dei flussi (Bug 443), e un 429 con quota
esaurita di LiteLLM è credito esaurito, permanente. Inoltre il fallimento del ciclo non riporta il motivo dato
dall'exchange quando rifiuta le credenziali.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): la permanenza la decide centralmente l'eccezione base, che sa quali codici
  sono bloccanti; gli adapter non si toccano; override solo per casi eccezionali, oggi nessuno. 401, 402 e 403
  sempre permanenti, 429 e 5xx sempre temporanei, gli altri codici come dichiara l'errore. Il motivo dell'exchange compare nel rifiuto delle credenziali.
- CLAUDE.md: ogni traduzione conserva la causa (`raise … from error`); domain senza librerie esterne.

## Opzioni considerate

1. `AutotradingError.permanent` diventa una proprietà calcolata: cerca nella catena `__cause__` il codice del sistema
   esterno (attributo `status_code` della causa, o `status_code` della sua `response`, letti per nome senza importare
   librerie): 401, 402 e 403 sempre permanenti, 429 e 5xx sempre temporanei; per ogni altro codice, o senza codice,
   vale il valore dichiarato dall'errore (default falso), così un rifiuto vero delle credenziali con 400 o 422 resta
   permanente. I casi speciali del 429 negli adapter (Hyperliquid, LiteLLM) si tolgono. `FlowCredentialsRefusedError`
   porta il motivo mascherato dell'exchange e `FlowCredentialsRejectedError` lo aggiunge al messaggio:
   «credenziali del conto non valide: <conto> (<motivo>)».
2. Il ciclo legge le cause: scartata, la regola starebbe nel ciclo e non nell'errore, e l'outbox la dovrebbe ripetere.

## Esito della decisione

Opzione 1.

Verifica: prova (unit test dell'errore base: 401/402/403 permanenti anche su un errore che non lo dichiara, 429 e 5xx
temporanei anche su un errore che si dichiara permanente, altro codice o nessuna causa = valore dichiarato; scenari di R1.2.4 aggiornati: motivo dell'exchange nel
rifiuto, limite di frequenza senza pausa).

### Conseguenze

- Un solo punto decide la permanenza per cicli e outbox; un adapter nuovo non deve sapere nulla dei codici bloccanti,
  basta conservare la causa.
