# ADR 0152 — Elenco degli exchange supportati esposto dall'API

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: R2.3.8 (Task 270)
- Collegate: ADR 0147 (asset del flusso dall'elenco dell'API), ADR 0116 (dashboard senza logica propria), ADR 0027

## Contesto e problema

La registrazione di un conto chiede il nome dell'exchange come testo libero; l'API rifiuta un exchange che non supporta
(`UnsupportedExchangeError`, dalla mappa degli exchange composta in `bootstrap.py`) ma non espone quella mappa. La
dashboard non può offrire un elenco senza inventarlo.

## Fattori decisionali

- ADR 0116: la dashboard non ha logica né dati di business che l'API non esponga.
- ADR 0147: gli asset del flusso vengono da `GET /assets`, un caso d'uso per elenco.
- `CLAUDE.md`: un caso d'uso per modulo con il solo `execute`; `bootstrap.py` senza decisioni.

## Opzioni considerate

### 1. Caso d'uso che elenca le chiavi della mappa già composta

- Pro: una sola fonte, la stessa che rifiuta un exchange non supportato; nessuna chiamata di rete.
- Contro: nessuno rilevante.

### 2. Elenco fisso nella configurazione dell'API

- Pro: semplice.
- Contro: seconda fonte da tenere allineata con gli adapter composti.

## Esito della decisione

Opzione 1. `ListSupportedExchangesUseCase` in `application/accounts/list_supported_exchanges.py` riceve la stessa
mappa `exchanges` di `RegisterAccountUseCase` e restituisce i nomi in ordine alfabetico. Il router
`GET /exchanges` (tag `conti`) li restituisce come `list[str]`; `openapi.json` e il client generato della dashboard si
rigenerano. Nessuna risposta d'errore propria: la mappa è in memoria.

Verifica: revisione.

### Conseguenze

- Un exchange aggiunto con il suo adapter compare nell'elenco senza altro lavoro.
