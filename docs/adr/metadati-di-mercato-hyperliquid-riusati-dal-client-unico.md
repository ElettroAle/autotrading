# ADR metadati-di-mercato-hyperliquid-riusati-dal-client-unico — Un client SDK Hyperliquid per processo, con i metadati di mercato in un decorator privato della cartella

- Stato: proposta (20 novembre 2026)
- Requisiti: Bug 635 (Task 639)
- Collegate: ADR cache-delle-letture-del-conto-come-decorator-in-memoria, ADR 0018; `.claude/rules/tech-hyperliquid.md`,
  `.claude/rules/layer-adapters.md`
- Verifica: prova

## Contesto e problema

`HyperliquidSdkAdapter.info()` ed `exchange()` costruiscono a ogni chiamata un `Info` (o un `Exchange`, che ne
costruisce uno) senza metadati: il costruttore della libreria scarica `spotMeta` (440 KB) e `meta`, 1,1–1,7 s misurati
il 20 novembre 2026, prima di ogni lettura. La lettura dello stato del conto lo fa tre volte (circa 4 s su 6),
un'attività una volta (circa metà del suo tempo). Ogni adapter Hyperliquid crea poi un proprio `HyperliquidSdkAdapter`.
La libreria accetta `meta` e `spot_meta` nel costruttore: con entrambi non fa nessuna chiamata.

## Fattori decisionali

- Decisione del proprietario (20 novembre 2026, in chat, punto 1 dell'analisi del Bug 635): un solo client SDK per
  processo, creato come singleton dalla composition; i metadati in memoria, riletti ogni ora; un client leggero a ogni
  lettura. Il proprietario ammette un decorator interno alla cartella, privato e mai usato fuori, se più manutenibile.
- ADR cache-delle-letture-del-conto-come-decorator-in-memoria: una cache è un decorator, con lo stato creato una volta
  dalla composition e mai in variabili di modulo. Qui la cosa decorata non è una porta ma la lettura dei metadati,
  interna all'SDK: il decorator resta privato di `hyperliquid/` per decisione del proprietario.
- CLAUDE.md: un `Protocol` sta solo in `ports.py`; una classe pubblica di una cartella adapter è un `*Adapter` o un
  `*Error`.
- `Info` usa una sessione HTTP propria: non si condivide tra thread, i metadati sì (dati immutabili).

## Decisione

- Lettura dei metadati in una classe privata della cartella (`_MarketMetadata`: `meta` e `spot_meta` per rete) e una
  sottoclasse privata decorator (`_CachedMarketMetadata`) che riceve la lettura da decorare e tiene per rete i
  metadati letti per un'ora, con un lock; scaduta l'ora li rilegge al primo uso. Un errore della lettura non si salva.
- `HyperliquidSdkAdapter` riceve la lettura dei metadati e costruisce ogni `Info` ed `Exchange` passando `meta` e
  `spot_meta`: un client nuovo e leggero a ogni chiamata, nessuna rete nel costruttore.
- `hyperliquid_adapters()` crea un solo `HyperliquidSdkAdapter` con i metadati decorati e lo passa a tutti gli
  adapter della cartella; i default dei costruttori restano per i test.
- La durata di un'ora sta nella configurazione della cartella con quel default.
- `tech-hyperliquid.md` nomina il client unico e il decorator privato dei metadati.

## Alternative scartate

- Riusare la stessa istanza di `Info`: la sua sessione HTTP non è sicura tra i thread del worker.
- Metadati letti all'avvio e mai aggiornati: un asset quotato dopo non si vede fino al rilascio successivo.
- Decorator in `process_memory/`: i metadati sono un dettaglio dell'SDK, non una porta.

## Conseguenze

- Un'attività scende da circa 2,5 a circa 1,1 s, la lettura dello stato del conto da circa 6 a circa 2 s (stima).
- Un asset quotato da Hyperliquid si vede al più dopo un'ora.
- Una chiamata in più ogni ora per rete e per processo.
