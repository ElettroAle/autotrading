# ADR movimenti-del-conto-nel-registro-con-cursore — Depositi, prelievi e trasferimenti del conto registrati col cursore del registro

- Stato: proposta (20 novembre 2026)
- Requisiti: Bug 635 (Task 641); R1.6.2, R3.3.1
- Collegate: ADR 0063 (registro delle operazioni), ADR 0076 (rilettura di un'ora del registro), ADR
  saldo-atteso-dalle-righe-del-registro-dopo-la-lettura-precedente; `.claude/rules/context-flows.md`,
  `.claude/rules/tech-hyperliquid.md`, `.claude/rules/tech-sqlalchemy.md`
- Verifica: prova

## Contesto e problema

`HyperliquidAccountActivityAdapter.activity` legge a ogni chiamata tutto il ledger dei movimenti del conto
(`user_non_funding_ledger_updates` da `startTime=0`) per riempire `AccountActivity.movements`. L'unico uso dei
movimenti è il saldo atteso della riconciliazione (movimenti successivi alla lettura precedente); la dashboard mostra
le variazioni non attribuibili, non `movements`. La lettura cresce con la vita del conto e si ripete per ogni lettura
dell'attività (cicli, dashboard).

## Fattori decisionali

- Decisione del proprietario (20 novembre 2026, in chat, punto 6 dell'analisi del Bug 635): leggere i movimenti da un
  cursore salvato invece che dall'inizio, come già per le esecuzioni.
- ADR 0063 e 0076: il registro legge solo ciò che è nuovo dal cursore con un'ora di sovrapposizione e scrive ogni riga
  una volta.
- ADR saldo-atteso-dalle-righe-del-registro-dopo-la-lettura-precedente: la riconciliazione spiega il saldo con le righe
  del registro tra la lettura precedente e quella corrente.

## Decisione

- I movimenti diventano righe del registro: `RecordAccountExecutionsUseCase` li legge con esecuzioni e funding, dalla
  stessa finestra (cursore meno un'ora), e il registro li scrive una volta in una tabella nuova
  `account_movements` (tenant, conto, identificativo del movimento, importo con segno, istante; RLS e vincolo di
  unicità), con indice per tenant, conto e istante. Il cursore conta anche i movimenti.
- La porta delle esecuzioni del conto restituisce anche i movimenti della finestra; l'adapter Hyperliquid li legge con
  `user_non_funding_ledger_updates(since)` e la traduzione dei tipi di oggi.
- La riconciliazione prende i movimenti dalle righe del registro successive alla lettura precedente
  (`recorded_after`), non più dall'attività.
- `AccountActivity` non ha più `movements`; l'attività non legge più il ledger dei movimenti (una chiamata in meno),
  né il worker li invia all'api.
- Lo storico delle variazioni di capitale (`transfers`) non cambia.

## Alternative scartate

- Passare all'attività l'istante da cui leggere: la porta dell'attività diventa dipendente dalla riconciliazione e la
  cache della dashboard deve distinguere le finestre.
- Leggere solo gli ultimi giorni: una lettura precedente più vecchia perderebbe movimenti.

## Conseguenze

- Ogni lettura dell'attività fa una chiamata Hyperliquid in meno e non cresce con la vita del conto.
- Al primo ciclo dopo il rilascio i movimenti si leggono dal cursore esistente meno un'ora: quelli precedenti alla
  lettura precedente erano già nel riferimento.
