# ADR prezzo-limite-dell-ordine-a-mercato-vicino-all-oracolo — Il prezzo limite dell'ordine a mercato resta vicino all'oracolo

- Stato: proposta (22 novembre 2026)
- Requisiti: Bug 631 (Task 704)
- Collegate: `domain/orders/slippage.py`; `.claude/rules/tech-hyperliquid.md`, `.claude/rules/context-orders.md`
- Verifica: prova

## Contesto e problema

L'ordine a mercato su Hyperliquid è un ordine limite IOC il cui prezzo limite l'SDK calcola dal prezzo medio del book
più o meno lo slippage massimo (`Exchange._slippage_price`, predefinito 5%). Il 20/11/2026 sulla testnet il book di BTC
stava circa il 2,5% sotto l'oracolo: la vendita aveva limite 60.350 × 0,95 ≈ 57.330, circa il 7,5% sotto l'oracolo, ed
è stata rifiutata con «Order price too far from oracle» (`oracleRejected`). Il ciclo non ha aperto né chiuso la
posizione. La documentazione di Hyperliquid elenca il rifiuto ma non pubblica l'ampiezza della fascia ammessa.

## Fattori decisionali

- Richiesta del proprietario (22/11/2026): sviluppare tutto in autonomia; nessuna regola scritta copre la scelta, la
  decido io col contratto come criterio.
- Lo slippage è «la distanza massima dal prezzo corrente che l'ordine a mercato accetta» (`Slippage`): il prezzo vero
  di riferimento dell'exchange è l'oracolo, non un book sottile.
- Le eccezioni dell'SDK si traducono nell'adapter; la regola di mercato resta in Decimal.

## Decisione

- L'adapter Hyperliquid degli ordini calcola da sé il prezzo limite dell'ordine a mercato, invece di lasciarlo
  all'SDK: per un acquisto il **minore** tra `medio × (1 + slippage)` e `oracolo × (1 + slippage)`, per una vendita il
  **maggiore** tra `medio × (1 − slippage)` e `oracolo × (1 − slippage)`, arrotondato al passo di prezzo del mercato
  come già fanno le protezioni (`rounded_price`). Il prezzo medio e l'oracolo (`oraclePx`) si leggono dal contesto
  dell'asset (`metaAndAssetCtxs`) nella stessa lettura.
- L'ordine resta IOC con il proprio `cloid`: si esegue al meglio del book entro il limite; la chiusura (`market_close`)
  segue la stessa regola.
- Il calcolo del limite è una funzione pura del domain degli ordini (Decimal), provata con unit test anche sul caso del
  20/11/2026; l'adapter la usa.
- Un rifiuto `oracleRejected` che arriva comunque resta tradotto nell'errore tipizzato esistente del rifiuto
  dell'ordine.

## Alternative scartate

- Slippage più basso: non risolve un book lontano dall'oracolo e restringe gli ordini anche dove il book è giusto.
- Limite solo dall'oracolo: su mainnet, con book profondo e allineato, cambierebbe senza motivo il comportamento di oggi.

## Conseguenze

- Con un book lontano dall'oracolo l'ordine può non trovare liquidità entro il limite: diventa un mancato riempimento
  IOC invece di un rifiuto per l'oracolo.
