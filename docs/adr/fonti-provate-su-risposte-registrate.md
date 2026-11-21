# ADR fonti-provate-su-risposte-registrate — I test di integrazione delle fonti girano su risposte vere registrate

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 699 (Task 700)
- Collegate: sostituisce, per le sole fonti, la parte «le fonti girano contro i servizi veri» di ADR
  nessun-test-escluso-o-saltato; estende ADR risposte-http-registrate-per-i-fornitori-a-chiave;
  `.claude/rules/tests.md`, `.claude/rules/ci.md`, `CLAUDE.md` (Test)
- Verifica: prova

## Contesto e problema

I cinque test `tests/integration/sources/test_*_live.py` (sentiment di alternative.me e CoinMarketCap, notizie RSS,
dati di mercato e storico dei prezzi dalla testnet Hyperliquid, volumi da Binance) chiamano i servizi veri a ogni PR.
Dai runner GitHub, con IP condivisi, l'endpoint pubblico del Fear & Greed di CoinMarketCap risponde 429: la PR #280
fallisce due volte su quel solo test, estraneo al suo lavoro, e resta bloccata. Un test che dipende dal limite di
richieste di un terzo non dice nulla sul codice della PR.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): «Registrate in pr e basta». I test di integrazione delle
  fonti girano in PR su risposte registrate; nessuna chiamata dal vivo alle fonti, in nessun punto della pipeline.
- ADR nessun-test-escluso-o-saltato: nessun test saltato o escluso; resta valida per tutto il resto (testnet per
  `orders` e `accounts`, fornitori IA).
- ADR risposte-http-registrate-per-i-fornitori-a-chiave: modello già usato per Arkham e LunarCrush.

## Decisione

- I cinque file `test_*_live.py` diventano `test_<fonte>_recorded.py` (marker `integration`, nessun salto) sul modello
  di `test_arkham_recorded.py`: le risposte stanno in `tests/integration/sources/recorded/<tecnologia>/` e sono
  risposte **vere** dei servizi, catturate una volta dal vivo e salvate così come arrivano (corpo JSON o XML del feed),
  ciascuna col file che dice da quale URL e in che data è stata registrata.
- Gli adapter `httpx` (alternative_me, coinmarketcap, rss, binance) si provano con `httpx.MockTransport` che risponde
  col file registrato e verifica anche la richiesta (URL, parametri, intestazioni). Gli adapter Hyperliquid delle fonti
  si provano con il trasporto o il client che già ricevono, alimentato dalle risposte registrate dell'endpoint `info`
  della testnet; se un adapter non riceve ancora il proprio client, il costruttore lo riceve (come per `httpx.Client`),
  senza cambiare comportamento.
- Le asserzioni di freschezza («indice di oggi», «storie recenti») diventano asserzioni sul contenuto registrato: date e
  valori del file. Si registra almeno una risposta di errore per fonte (429 o 5xx) per provare la traduzione nell'errore
  tipizzato.
- `tests.md`, `ci.md` e la sezione Test di `CLAUDE.md` dicono che le fonti si provano su risposte registrate; i sistemi
  veri in pipeline restano testnet Hyperliquid per `orders` e `accounts` e i fornitori IA.

## Alternative scartate

- Nuovi tentativi o attesa sul 429: il limite dei runner condivisi non dipende da noi, la PR resterebbe ostaggio.
- Test dal vivo in un job pianificato fuori dalla PR: il proprietario non li vuole («e basta»).
- Libreria di registrazione (vcrpy, respx): `MockTransport` basta, come già deciso.

## Conseguenze

- Un cambio del formato di una fonte non si vede nei test finché non si ri-registra la risposta: si vede dal ciclo
  reale (errore della fonte nel registro e campanella).
- Le PR non dipendono più dalla disponibilità né dai limiti delle fonti.
