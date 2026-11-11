# ADR 0028 — Catalogo delle fonti: definizioni nel domain, composizione in bootstrap

- Stato: accettata (11 novembre 2026)
- Requisiti: R1.3.1 (Task T1.3.1.1)

## Contesto

R1.3.1 chiede un catalogo delle fonti consultabile, con nome, descrizione e parametri (valore
predefinito e valori ammessi). Una fonte aggiunta alla piattaforma deve comparire nel catalogo e diventare
selezionabile nei flussi senza altre modifiche; una fonte ritirata deve sparire. Le fonti di E1 sono
indicatori, pivot, forecast, due fonti sentiment (alternative.me e CoinMarketCap, due indici
diversi con lo stesso nome, entrambi voluti dal proprietario) e notizie. Il loro calcolo e la loro raccolta arrivano con
R1.3.3-R1.3.7.

## Decisione

- **Definizione nel domain di `sources`.** `SourceDefinition` (nome, descrizione, per asset o di mercato,
  parametri) e `SourceParameter` (chiave, etichetta, predefinito, minimo, massimo; un predefinito fuori
  intervallo è un difetto e solleva `InvalidSourceParameterError`). Ogni famiglia di fonti ha un modulo
  proprio con le sue definizioni (`indicators.py`, `pivots.py`, `forecast.py`, `news.py`, e `sentiment.py`
  con le due fonti Fear & Greed): lì arriveranno anche i loro calcoli.
- **`SourceCatalog`** compone le definizioni nell'ordine dato e trova una fonte per nome; una fonte assente
  solleva `SourceNotAvailableError` "fonte non disponibile: <nome>" (404).
- **Composizione in `bootstrap.py`** (`SOURCE_CATALOG`). Aggiungere o ritirare una fonte significa cambiare
  quella sola riga: chi legge il catalogo non cambia.
- **Casi d'uso** `ListSourcesUseCase` e `GetSourceUseCase`; **API** `GET /sources` e `GET /sources/{nome}`,
  dietro l'autenticazione come ogni funzione.
- **Nomi**: la fonte si identifica con il nome di business del requisito (`indicatori`, `notizie`); un
  parametro ha una chiave senza spazi (`numero_notizie`), usata nella configurazione del flusso, e
  un'etichetta (`numero notizie`), usata nei motivi di rifiuto.

## Alternative scartate

- **Catalogo in configurazione o in database**: una fonte senza codice che la raccolga non è utilizzabile;
  la definizione appartiene al codice della fonte.
- **Registro automatico per scoperta dei moduli**: nasconde quali fonti sono attive; una riga esplicita in
  `bootstrap.py` è la stessa quantità di modifica e si legge.

## Conseguenze

- `flows` valida fonti e parametri della configurazione attraverso una porta propria collegata a questo
  catalogo in `bootstrap.py` (indipendenza tra contesti, ADR 0026).
- I file `.feature` di E1 entrano tutti in `specs/E1-flussi-autonomi/`, con `@wip` finché il requisito non
  è consegnato.
