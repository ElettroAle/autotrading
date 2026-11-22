# ADR parametri-delle-fonti-come-liste-libere — Orizzonti, periodi e finestre delle fonti come liste libere

- Stato: proposta (22 novembre 2026)
- Requisiti: Bug 706 (Task 707)
- Collegate: sostituisce, per i parametri nominati sotto, ADR tendenza-lunga-sulle-candele-giornaliere (flag e orizzonti
  fissi), ADR indicatori-estesi-nel-domain (flag `fibonacci`, `gann`, `ciclo` e `candele_estese`), ADR
  orizzonti-lunghi-del-forecast (orizzonte lungo a scelta) e i periodi fissi di ADR 0032/0057; ADR 0083 (intervalli
  dichiarati dall'exchange); R1.1.3 (configurazione versionata); `.claude/rules/context-sources.md`
- Verifica: prova

## Contesto e problema

Le fonti hanno orizzonti, periodi e finestre fissi nel codice, o accesi da un flag 0/1 con valori fissi dietro: un
utente non può chiedere la variazione a 90 giorni, una EMA a 200 o un RSI a 21, né più finestre di Fibonacci.

## Fattori decisionali

- Decisione del proprietario (22 novembre 2026, in chat): gli orizzonti si impostano quanti se ne vuole e al numero che
  si vuole; nessun numero fisso di valori, nessun flag; «va fatto per tutto dove è possibile».
- Calcoli nel domain in Decimal; candele chiuse dell'exchange; intervalli di candela dichiarati dall'exchange (ADR 0083).
- La configurazione dei flussi è versionata: una versione esistente resta leggibile.

## Decisione

- **Nuovo tipo di parametro** nel domain: parametro a **lista di interi** (es. `SourceListParameter`), con chiave,
  etichetta, valore predefinito (una lista, anche vuota), minimo e massimo di ogni elemento. Nessun limite al numero di
  elementi oltre a quello che rende i valori distinti e ordinati; lista vuota = valore spento. Il catalogo delle fonti,
  la validazione della configurazione, l'API (schema e messaggi di rifiuto) e l'editor della dashboard (campo che
  accetta più numeri) lo trattano come gli altri parametri; i parametri interi restano per i valori singoli.
- **Parametri trasformati** (chiave, unità, intervallo di ogni elemento, predefinito):
  - indicatori: `medie_periodi` (candele, 2-500, [20, 50]) per EMA e MA; `rsi_periodi` (candele, 2-200, [7, 14]);
    `macd_veloce`, `macd_lento`, `macd_segnale` (interi singoli, 12, 26, 9, con veloce < lento); `timeframe_minuti`
    (minuti, intervalli dichiarati dall'exchange, [240]): timeframe in più oltre a quello del ciclo, ciascuno con la sua
    serie; i nomi dei valori nominano periodo e timeframe (es. `240m.EMA200`, con le etichette di `Timeframe.label`).
  - tendenza lunga: `tendenza_giorni` (giorni, 1-1000, []) per le variazioni; `canale_giorni` (giorni, 2-1000, []) per
    massimo e minimo delle chiusure precedenti l'ultima; le candele giornaliere si leggono solo se una lista non è vuota,
    quante ne servono per il valore più lungo.
  - indicatori estesi: `fibonacci_candele`, `gann_candele`, `ciclo_candele` (candele del timeframe lungo, 10-1000, []):
    una serie di valori per ogni finestra; spariscono i flag e `candele_estese`.
  - forecast: `orizzonti_minuti` (minuti, 15-43200, [15, 60]) sostituisce gli orizzonti brevi fissi e la scelta
    dell'orizzonte lungo; la profondità dello storico si sceglie per ciascun orizzonte con la regola di oggi (storico
    lungo per gli orizzonti di almeno un giorno).
  - pivot: `pivot_giorni` (giorni, 1-365, [1]): pivot calcolati sul massimo, minimo e chiusura degli N giorni UTC chiusi
    precedenti, una serie per ogni valore.
- Restano interi singoli i valori che sono già un numero libero (numero e età delle notizie, soglia delle balene,
  numero dei messaggi social, profondità dello storico, lunghezza della serie).
- **Configurazioni esistenti**: una migrazione dei dati traduce le versioni salvate senza perdere il comportamento
  (`tendenza_lunga=1` → `tendenza_giorni=[7,14,30,60]`, `canale_giorni=[20]`; `fibonacci=1` →
  `fibonacci_candele=[candele_estese]`, e così per gann e ciclo; orizzonte lungo scelto → aggiunto a `orizzonti_minuti`).
  Le versioni restano versioni: la migrazione riscrive i parametri, non crea versioni nuove.
- Gli scenari dei requisiti toccati (R1.3.x degli indicatori, R5.1.4, R5.1.5, R5.1.6 e quelli dei pivot e del forecast)
  si aggiornano ai nomi nuovi e aggiungono un caso con valori scelti dall'utente.

## Alternative scartate

- Numero fisso di parametri numerici (es. quattro orizzonti): il proprietario lo ha rifiutato.
- Testo libero da interpretare: la validazione dei singoli valori deve restare tipizzata.

## Conseguenze

- I nomi dei valori nel contesto dell'agente cambiano: le istruzioni dei flussi che li citano vanno riviste.
- Più valori costano più candele e più token: la lettura chiede solo le candele necessarie al valore più lungo.
