# ADR 0166 — Cambi dell'indirizzo della pagina che si sommano anche in rapida successione

- Stato: proposta (15 novembre 2026)
- Requisiti: Bug 291 (Task 292)
- Collegate: ADR 0139 (scheda e filtri dello storico nell'indirizzo), ADR 0123 (periodo nell'indirizzo), ADR 0163
  (scenari che attendono uno stato), ADR 0116

## Contesto e problema

Scheda, filtri, periodo, ordinamento e flussi confrontati vivono nell'indirizzo della pagina (ADR 0123, ADR 0139).
Ogni hook li cambia con `setSearchParams((current) => ...)`. La documentazione di React Router dichiara che la forma
a funzione **non** accoda come `setState`: `current` è l'indirizzo dell'ultima resa, e più chiamate prima della resa
successiva non si sommano. Con un dispositivo lento, una scelta fatta prima che la pagina mostri la precedente la
cancella (Bug 291, emerso dal Bug 289).

## Fattori decisionali

- `CLAUDE.md`, Dashboard: struttura di bulletproof-react; il codice condiviso fra funzionalità sta fuori da
  `src/features`, nessun import fra funzionalità.
- ADR 0123 e ADR 0139: l'indirizzo resta l'unica fonte di scheda, filtri e periodo (link e ricarica).
- Documentazione di React Router 8 (`useSearchParams`): per sommare più cambi serve gestire la coda a mano.
- Nessuna libreria nuova.

## Opzioni considerate

### 1. Un solo hook condiviso che somma ogni cambio all'ultimo indirizzo richiesto

- Pro: tutte le pagine si correggono in un punto; l'indirizzo resta l'unica fonte; prova unitaria semplice (due cambi
  nello stesso tick, entrambi nell'indirizzo).
- Contro: un piccolo stato condiviso da tenere allineato all'indirizzo.

### 2. Stato locale React (`useState`) per scheda e filtri, sincronizzato nell'indirizzo con un effetto

- Pro: accoda come React.
- Contro: due fonti della stessa scelta; contraddice ADR 0123 e ADR 0139.

### 3. Bloccare i controlli finché la pagina non mostra il cambio precedente

- Pro: nessuna coda.
- Contro: interfaccia che ignora i clic; non risolve, sposta il problema.

## Esito della decisione

Opzione 1. Un hook condiviso in `dashboard/src/hooks/` (per esempio `useSearchChange`) restituisce la funzione che
cambia l'indirizzo: ogni cambio parte dall'ultimo indirizzo **richiesto**, non da quello dell'ultima resa. L'ultimo
indirizzo richiesto è uno solo per tutta la pagina (lo condividono gli hook di storico, periodo, ordinamento e flussi
confrontati, che sulla stessa pagina cambiano lo stesso indirizzo) e torna a coincidere con l'indirizzo della pagina
appena questa lo mostra o quando l'indirizzo cambia da fuori (navigazione, indietro). Gli hook che oggi chiamano
`setSearchParams` con una funzione passano tutti da lì; un'assegnazione completa (`setSearchParams({...})`) che
sostituisce l'intero indirizzo resta com'è.

Verifica: prova (prova unitaria: due cambi di parametri diversi, e un cambio di scheda seguito da un cambio di periodo,
nello stesso tick finiscono entrambi nell'indirizzo; prova di architettura: nessun `setSearchParams(` con una funzione
fuori dall'hook condiviso).

### Conseguenze

- Un nuovo parametro dell'indirizzo si cambia dall'hook condiviso, o la prova lo segnala.
- Le attese degli scenari dell'ADR 0163 restano: provano lo stato osservabile, non sostituiscono la correzione.
