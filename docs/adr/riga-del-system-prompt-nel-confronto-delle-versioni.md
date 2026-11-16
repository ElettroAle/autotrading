# ADR riga-del-system-prompt-nel-confronto-delle-versioni — Riga del system prompt nel confronto delle versioni

- Stato: accettata (16 novembre 2026)
- Requisiti: R2.3.5, R1.4.8 (Bug 441, Task 442)
- Collegate: ADR system-prompt-del-flusso-come-modello-con-segnaposti, ADR 0133 (confronto delle versioni)

## Contesto e problema

Con R1.4.8 il system prompt è una parte della configurazione del flusso: l'API lo restituisce in ogni versione
(`GET /flows/{id}/versions/{n}`, campi `system_prompt` e `system_prompt_is_default`) e lo confronta col nome di parte
"system prompt" ("predefinito" quando la versione segue la piattaforma). La tabella del confronto della dashboard si
costruisce da un elenco fisso di parti (`configuration-rows.ts`) che non lo comprendeva: un prompt non cambiato non
compariva affatto, uno cambiato compariva solo in fondo, tra le parti che la dashboard non elenca, e il testo su più
righe perdeva gli a capo.

## Fattori decisionali

- La tabella evidenzia le righe col nome di parte che le differenze dell'API riportano: i nomi e i testi della
  dashboard devono essere gli stessi dell'API.
- Un campo nuovo della configurazione non deve poter restare fuori dal confronto senza che una prova lo segnali.
- Nessuna logica che l'API non esponga.

## Opzioni considerate

### 1. Riga "system prompt" nell'elenco, valore come nelle differenze dell'API, prova legata ai tipi dell'API

- La riga si aggiunge a `configuration-rows.ts` col nome "system prompt", valore "predefinito" se
  `system_prompt_is_default`, altrimenti `system_prompt`, come fa il domain in `configuration_difference.py`.
- Le celle del confronto conservano gli a capo (`whitespace-pre-wrap`).
- Lo unit test dell'elenco associa ogni campo di `ConfigurationResponse` (tipi generati dall'OpenAPI) ai nomi di parte
  che l'API ne ricava, con `satisfies Record<keyof ConfigurationResponse, ...>`: un campo nuovo dell'API rompe il
  controllo dei tipi finché non è collocato, e la prova verifica che le righe siano esattamente quelle parti.

### 2. Mostrare il testo predefinito per intero

Il confronto direbbe una cosa diversa dalle differenze dell'API, che lo chiamano "predefinito": scartata.

### 3. Nomi delle parti esposti dall'API

Un endpoint con l'elenco delle parti eviterebbe di ripeterle nella dashboard, ma cambia l'API per un difetto della
sola dashboard; la prova legata ai tipi generati basta a impedire che un campo resti fuori: scartata.

## Esito della decisione

Opzione 1: corregge il confronto senza toccare l'API e rende rosso, già al controllo dei tipi, il prossimo campo
della configurazione dimenticato.

## Conseguenze

- Il confronto mostra sempre il system prompt, al suo posto, evidenziato quando cambia e con le sue righe.
- Il finto dell'API conserva il system prompt di ogni versione e lo confronta come l'API.
- Aggiungere un campo a `ConfigurationResponse` richiede di collocarlo nella prova dell'elenco.
