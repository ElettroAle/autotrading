# ADR 0083 — Intervalli di candela dichiarati dall'exchange

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.3.3 (Task T1.3.3.1); Bug 172
- Collegate: ADR 0057 (dati di mercato e lettura degli indicatori), di cui sostituisce solo la provenienza degli
  intervalli di candela; ADR 0043 (storico dei prezzi per la previsione)

## Contesto

L'ADR 0057 sceglie il timeframe breve degli indicatori tra gli intervalli di candela dell'exchange: l'intervallo
uguale all'intervallo di ciclo o, se manca, il più fine sotto di esso. Quella lista viveva nel domain, insieme ai
nomi con cui Hyperliquid chiama ciascun intervallo (`1m`, `4h`, `1d`), e l'adapter passava all'SDK il nome scritto
nel domain. Il domain conosceva quindi una tecnologia: un exchange con intervalli diversi, o con altri nomi per gli
stessi, avrebbe richiesto di cambiare una regola di business.

La regola di scelta è di dominio; quali intervalli esistono e come si chiamano è un fatto dell'exchange.

## Decisione

- **Domain**: `Timeframe` è solo una durata in minuti. Il nome che l'agente legge nel contesto (`breve.timeframe`,
  `lungo.timeframe`) deriva dai minuti con l'unità intera più grande (`15m`, `4h`, `1d`) e resta uguale a prima per
  tutti gli intervalli usati.
- **Regola**: `short_timeframe_of(cycle_minutes, available)` sceglie tra gli intervalli ricevuti il più grande non
  oltre l'intervallo di ciclo, in qualunque ordine arrivino. Se nessuno è abbastanza fine solleva
  `TimeframeNotAvailableError` (domain). Il timeframe lungo resta di 4 ore.
- **Porta**: `MarketDataPort.timeframes()` dichiara gli intervalli che l'exchange pubblica. `candles` su un
  intervallo fuori da quella lista solleva `TimeframeNotSupportedError` (application), senza interrogare l'exchange.
- **Adapter Hyperliquid**: un'unica mappa minuti → nome dell'intervallo di `candleSnapshot` (da 1 minuto a 1
  settimana). Da essa derivano `timeframes()`, il nome passato all'SDK, la candela giornaliera dei pivot e gli
  intervalli dello storico dei prezzi per la previsione (fino a un'ora, ADR 0043). L'intervallo mensile (`1M`) è
  escluso perché non ha una durata fissa in minuti.
- **Caso d'uso**: `ReadIndicatorsUseCase` riceve gli intervalli dalla porta che legge le candele.

## Alternative scartate

- **Lasciare la lista nel domain senza i nomi**: toglie la parola di Hyperliquid ma lascia nel domain quali
  intervalli esistono, che resta un fatto di un exchange.
- **Una porta dedicata agli intervalli**: separa due informazioni che vengono dalla stessa fonte e vanno sempre
  insieme; chi legge le candele deve poter dire su quali intervalli le dà.
- **Passare all'adapter il nome generato dal domain**: funziona finché i nomi coincidono per caso; il mese, o un
  exchange che scrive `60` invece di `1h`, lo romperebbe in silenzio.

## Conseguenze

- Il comportamento non cambia: per ogni intervallo di ciclo da 1 a 1440 minuti il timeframe breve, le candele chieste
  a Hyperliquid e i valori nel contesto dell'agente sono gli stessi di prima.
- Un nuovo exchange dichiara i propri intervalli e i propri nomi nel suo adapter, senza toccare domain e application.
- Una lista sola per gli intervalli di Hyperliquid: la previsione e gli indicatori non possono più divergere sui nomi.
