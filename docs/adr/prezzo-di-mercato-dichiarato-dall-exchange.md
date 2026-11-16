# ADR prezzo-di-mercato-dichiarato-dall-exchange — Prezzo di mercato dichiarato dall'exchange per ogni posizione

- Stato: accettata (16 novembre 2026)
- Requisiti: R1.4.7 (US 432, Task 434), R1.4.3, R2.3.11
- Collegate: ADR hyperliquid-testnet-come-adapter-dedicato, ADR 0038 (contesto e risposta dell'agente nel domain)

## Contesto e problema

Il contesto dell'agente porta già il PnL non realizzato letto dall'exchange del conto, ma non il prezzo corrente con
cui l'exchange valuta la posizione, e nessuna regola dice quale riferimento usare. Le fonti di mercato leggono la rete
reale (R2.3.11). Nella notte tra il 15 e il 16 novembre 2026 il flusso `prova-btc`, su Hyperliquid Testnet, ha chiuso
due short in profitto come stop loss: l'agente ha ricalcolato la perdita confrontando il prezzo di ingresso con il
prezzo delle fonti, circa il 2% sopra quello della testnet.

## Fattori decisionali

- La soluzione vale per ogni exchange presente e futuro: domain e application non nominano exchange né reti.
- Le fonti di mercato restano sulla rete reale (R2.3.11): gli indicatori della rete di test non sono affidabili.
- L'agente deve avere un prezzo dell'exchange da confrontare con quello delle fonti, non solo un PnL.

## Opzioni considerate

### 1. Prezzo di mercato obbligatorio nella posizione letta da ogni exchange, più una regola operativa generica

- La posizione letta da ogni exchange (`Position` in accounts, `CyclePosition` e `AccountPosition` in flows) ha il
  campo obbligatorio `mark_price`: ogni adapter exchange lo dichiara.
- Il campo arriva a `PositionView` (flows e agent) e al documento del ciclo come `prezzo_di_mercato`; il trasporto
  worker-api e le risposte di stato del conto, dell'attività e del flusso lo portano come `mark_price`.
- Le regole operative del messaggio di sistema dicono, senza nominare exchange o reti, di valutare e gestire le
  posizioni aperte solo con prezzo di mercato e PnL non realizzato dello stato del flusso; i prezzi delle fonti servono
  a stimare la direzione del mercato.
- Hyperliquid: `positionValue / |szi|` dal `clearinghouseState`, il valore della posizione al mark, nella stessa
  lettura e per entrambe le reti. Un valore assente, non numerico o una dimensione zero è una risposta di forma
  inattesa: l'errore di indisponibilità già previsto dal contratto.

### 2. Correggere il prezzo delle fonti con lo scarto tra le reti

Specifico di un exchange e fragile: lo scarto cambia nel tempo e non esiste per un exchange senza rete di test.

### 3. Fonti di mercato dalla rete del conto

Contraddice R2.3.11; gli indicatori della rete di test non sono affidabili.

### 4. Solo la regola nel messaggio di sistema

L'agente non avrebbe un prezzo dell'exchange da confrontare con quello delle fonti.

## Esito della decisione

Opzione 1: è generica (un campo del contratto della porta, non un ramo per exchange), non tocca le fonti e dà
all'agente il dato e la regola insieme.

## Conseguenze

- Un nuovo exchange non si integra senza il prezzo di mercato delle sue posizioni.
- La dashboard non mostra ancora il prezzo di mercato (fuori ambito); l'API lo espone già.
