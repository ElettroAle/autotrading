# ADR tendenza-lunga-sulle-candele-giornaliere — Variazioni a più giorni e canale giornaliero nella fonte indicatori

- Stato: proposta (21 novembre 2026)
- Requisiti: US 701 R5.1.6 (Task 702)
- Collegate: ADR 0032 (calcoli in Decimal nel domain), ADR 0057 (dati di mercato e lettura degli indicatori), ADR
  indicatori-estesi-nel-domain; `.claude/rules/context-sources.md`
- Verifica: prova

## Contesto e problema

La fonte «indicatori» legge al massimo 50 candele del timeframe lungo (4 ore, circa 8 giorni): il prezzo di 14 o 30
giorni fa non arriva all'agente. R5.1.6 chiede, dietro un parametro spento come predefinito, variazioni a 7, 14, 30 e
60 giorni, canale delle chiusure dei 20 giorni precedenti l'ultima e ultima chiusura giornaliera con l'istante, sulle
candele giornaliere chiuse dello stesso adapter dei dati di mercato.

## Fattori decisionali

- Requisito R5.1.6: perimetro solo dati nella fonte esistente, nessuna regola di apertura; parametro come fibonacci,
  gann e ciclo di R5.1.4 (ADR indicatori-estesi-nel-domain).
- Calcoli nel domain in Decimal sulle candele dell'exchange (ADR 0032, ADR 0057); la porta `MarketDataPort.candles`
  restituisce solo candele chiuse e l'adapter Hyperliquid offre già il timeframe di un giorno.
- Nessuna regola copre dove dichiarare un orizzonte senza storico: i dati mancanti del contesto sono oggi per fonte
  (R1.2.5). Scelta: dichiararli dentro i valori della fonte, come la nota di storico corto di R5.1.4.

## Decisione

- **Parametro** `tendenza_lunga` («tendenza lunga») della fonte indicatori, da 0 a 1, predefinito 0, valido per ogni
  adapter dei dati di mercato; entra nel catalogo dei parametri come quelli di R5.1.4.
- **Lettura**: solo col parametro a 1, `ReadIndicatorsUseCase` chiede `candles(asset, Timeframe(1 giorno), 61, now)`
  allo stesso `MarketDataPort`; col parametro a 0 nessuna lettura giornaliera. Un adapter senza il timeframe di un
  giorno solleva l'errore esistente `TimeframeNotAvailableError`.
- **Calcolo** in un modulo nuovo `domain/sources/long_trend.py`, sulle candele giornaliere chiuse in ordine:
  - `tendenza.variazione_<N>g` per N = 7, 14, 30, 60: `(ultima chiusura / chiusura di N candele prima − 1) × 100`;
    serve almeno N + 1 candele;
  - `tendenza.massimo_20g` e `tendenza.minimo_20g`: massimo e minimo delle chiusure delle 20 candele che precedono
    l'ultima; serve almeno 21 candele;
  - `tendenza.ultima_chiusura` e `tendenza.ultima_chiusura_istante` (istante di chiusura in ISO 8601 UTC);
  - `tendenza.dati_mancanti`: i valori senza storico sufficiente, con il numero di candele disponibili (es.
    «variazione_30g, variazione_60g, massimo_20g, minimo_20g: storico di 20 giorni chiusi»); assente se nulla manca.
- I numeri passano per lo stesso `text_of` degli altri valori della fonte.

## Alternative scartate

- Nuova fonte separata: il requisito chiede dati in più nella fonte esistente.
- Ricavare i giorni dalle candele a 4 ore: servirebbero 360 candele per 60 giorni, oltre il limite della lettura, e
  la giornata UTC non coinciderebbe per costruzione.
- Dichiarare l'orizzonte mancante nei dati mancanti del contesto dell'agente: cambierebbe il contratto delle fonti
  (dati mancanti per fonte, R1.2.5) per un solo valore.

## Conseguenze

- Col parametro acceso ogni ciclo fa una lettura in più all'exchange per asset.
- Il catalogo della fonte cresce di un parametro; l'editor lo genera da solo.
