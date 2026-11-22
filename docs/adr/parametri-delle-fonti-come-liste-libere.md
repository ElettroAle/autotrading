# ADR parametri-delle-fonti-come-liste-libere — Periodi, orizzonti e finestre delle fonti come liste libere

- Stato: proposta (22 novembre 2026)
- Requisiti: Bug 706 (Task 707, 708, 709, 710, 711, 712, 713), sotto US 701 R5.1.6
- Collegate: sostituisce, per i parametri nominati sotto, ADR tendenza-lunga-sulle-candele-giornaliere (flag e orizzonti
  fissi), ADR indicatori-estesi-nel-domain (flag `fibonacci`, `gann`, `ciclo` e `candele_estese`), ADR
  orizzonti-lunghi-del-forecast (orizzonti brevi fissi e orizzonte lungo a scelta) e i periodi fissi delle medie e
  dell'RSI di ADR 0057; R1.1.3 (configurazione versionata); `.claude/rules/context-sources.md`
- Verifica: prova

## Contesto e problema

Le fonti hanno periodi, orizzonti e finestre fissi nel codice, o accesi da un flag 0/1 con valori fissi dietro: un
utente non può chiedere la variazione a 90 giorni, una EMA a 200, un RSI a 21, più finestre di Fibonacci o un forecast
a 4 ore. Una strategia nuova richiede codice invece di configurazione.

## Fattori decisionali

- Requisito del proprietario (22 novembre 2026, Bug 706 e commento «Rettifica» su US 701): ogni periodo, orizzonte o
  finestra è una lista di numeri; regole comuni (ordine senza doppioni, lista vuota = spento, nomi con il numero, dati
  mancanti per valore, giornate UTC chiuse); un parametro a lista nuovo si aggiunge solo dichiarandolo nella fonte;
  gann e ciclo come Fibonacci; MACD e timeframe restano come oggi.
- Rettifica del proprietario: il requisito è agnostico rispetto all'exchange, nessun massimo deriva da quante candele
  conserva un mercato. Minimi: `medie_periodi` 2, `rsi_periodi` 2, `tendenza_giorni` 1, `canale_giorni` 2,
  `volume_relativo_candele` 2, `pivot_giorni` 1, `fibonacci_candele` 10. Un valore che chiede più storico di quello che
  l'adapter del mercato può dare va tra i dati mancanti. Tetto di sicurezza, numero massimo di valori e limiti di
  `orizzonti_minuti` si fissano nel design (qui sotto).
- Decisione del proprietario: nessuna migrazione nel codice; le configurazioni salvate in dev si traducono a mano una
  volta dopo il rilascio (Task 713), con `medie_periodi` [20, 50] e `rsi_periodi` [7, 14].
- Calcoli nel domain in Decimal; candele chiuse dell'exchange (ADR 0032, ADR 0057).

## Decisione

- **Parametro a lista** nel domain delle fonti (es. `SourceListParameter`), accanto a `SourceParameter`: chiave,
  etichetta, predefinito (lista, anche vuota), minimo e tetto di sicurezza di ogni valore, numero massimo di valori.
  Controllo comune: valori interi nell'intervallo, al massimo il numero dichiarato, salvati ordinati e senza doppioni;
  motivi di rifiuto «<etichetta>: ogni valore tra <minimo> e <tetto>» e «<etichetta>: al massimo <n> valori».
- **Tetto di sicurezza e numero massimo** (scelte del design, non limiti dello storico): ogni lista ha al massimo **8**
  valori; il tetto di ogni valore è **10000** per i parametri in candele e **3650** per quelli in giorni. Servono solo a
  non far chiedere all'exchange letture e calcoli fuori misura; lo storico che manca si dichiara, non si rifiuta.
- **Dichiarazione unica**: catalogo delle fonti, controllo della configurazione del flusso, schema e rifiuti dell'API ed
  editor della dashboard (campo che accetta più numeri, con intervallo e massimo dalla dichiarazione) ricavano tutto
  dalla dichiarazione del parametro; nessun codice per singolo parametro.
- **Parametri** (chiave, intervallo di ogni valore, predefinito):
  - indicatori: `medie_periodi` (2-10000, [20, 50]) per EMA e MA; `rsi_periodi` (2-10000, [7, 14]);
    `volume_relativo_candele` (2-10000, []): volume dell'ultima candela chiusa diviso la media delle N precedenti, sul
    timeframe breve e su quello lungo. I nomi dei valori portano il periodo (`EMA200`, `RSI21`, `volume_relativo42`).
  - tendenza lunga: `tendenza_giorni` (1-3650, []) per le variazioni percentuali tra l'ultima chiusura giornaliera e
    quella di N giorni prima; `canale_giorni` (2-3650, []) per massimo, minimo e punto medio delle chiusure degli N
    giorni precedenti l'ultima. Le candele giornaliere si leggono solo se almeno una lista non è vuota, quante ne
    servono per il valore più lungo.
  - indicatori estesi: `fibonacci_candele`, `gann_candele`, `ciclo_candele` (10-10000, []) sulle candele del timeframe
    lungo, una serie di valori per finestra; spariscono i flag e `candele_estese`.
  - forecast: `orizzonti_minuti` (15-43200, cioè da 15 minuti a 30 giorni, [15, 60]) sostituisce gli orizzonti brevi
    fissi e la scelta dell'orizzonte lungo; la profondità dello storico segue la regola di oggi (storico lungo per gli
    orizzonti di almeno un giorno).
  - pivot: `pivot_giorni` (1-3650, [1]): pivot sul massimo, minimo e chiusura degli N giorni UTC chiusi precedenti, una
    serie per valore.
- **Storico insufficiente**: un valore della lista che lo storico dato dall'adapter del mercato non permette di
  calcolare si dichiara tra i dati mancanti della fonte con il suo nome; gli altri valori della lista arrivano comunque.
- MACD, timeframe e gli altri parametri interi (notizie, balene, social, profondità dello storico, lunghezza della
  serie) restano come oggi.
- **Configurazioni salvate**: nessuna migrazione nel codice; la traduzione dei parametri salvati in dev si fa a mano una
  volta dopo il rilascio (Task 713): `tendenza_lunga`=1 → `tendenza_giorni` [7, 14, 30, 60] e `canale_giorni` [20];
  `fibonacci`/`gann`/`ciclo`=1 → `*_candele` [candele_estese]; `medie_periodi` [20, 50] e `rsi_periodi` [7, 14].
- **Scenari**: quelli del Bug 706 stanno sotto R5.1.6 (cartella rinominata
  `R5.1.6-parametri-a-lista-per-le-fonti-di-mercato`), divisi per sistema; gli scenari di R1.3.x, R5.1.4 e R5.1.5 che
  usano i parametri tolti si aggiornano ai nomi nuovi.

## Alternative scartate

- Massimi legati allo storico di un mercato: il requisito è agnostico rispetto all'exchange.
- Numero fisso di parametri numerici (es. quattro orizzonti): rifiutato dal proprietario.
- Migrazione Alembic dei dati con test: rifiutata dal proprietario, la traduzione è una tantum.

## Conseguenze

- I nomi dei valori nel contesto dell'agente cambiano: le istruzioni dei flussi che li citano vanno riviste.
- Più valori costano più candele e più token: la lettura chiede solo le candele necessarie al valore più lungo.
