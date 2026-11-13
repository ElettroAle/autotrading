# ADR 0095 — Margine isolato per ogni posizione

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.3.1, R0.4.1, R1.5.4, RF-03.03; Bug B0.3.1 (180)
- Supera: la parte di ADR 0022 che imposta la leva «in cross» (`update_leverage` con `is_cross=True`)
- Adegua: ADR 0067 (un solo margine, quello dell'exchange), nel contesto e nelle conseguenze legate al cross
- Collegate: docs/architecture.md §6 (porta dell'exchange), ADR 0062 (stato attribuito nel ciclo), ADR 0079
  (importo della procedura di verifica)

## Contesto e problema

`docs/architecture.md:178` prescrive `set_leverage(asset, leverage, isolated=True)`. L'adapter Hyperliquid chiamava
invece `Exchange.update_leverage(leverage, coin, True)`: nell'SDK installato la firma è
`update_leverage(self, leverage, name, is_cross=True)`, quindi ogni posizione si apriva con margine incrociato
(ADR 0022: «`update_leverage` in cross»).

Con margine incrociato tutte le posizioni del conto usano il saldo intero come garanzia. Più flussi possono
condividere un conto (RF-03.03): la perdita di una posizione consuma il margine delle altre e, nel caso peggiore, una
liquidazione chiude anche posizioni di altri flussi. Il capitale allocato a un flusso era un limite della
piattaforma, non dell'exchange.

## Decisione

- **Regola nel dominio** (`domain/orders/margin_mode.py`): `MarginMode` (`ISOLATED`, `CROSS`) e
  `MarginMode.per_position()`, che per ogni posizione della piattaforma è `ISOLATED`.
- **Porta** `ExchangePort.set_leverage(access, coin, leverage, margin)`: il modo di margine arriva dal caso d'uso, non
  è scelto dall'adapter.
- **Casi d'uso**: `OpenPositionUseCase` (procedura di verifica, R0.4.1) e `ExecuteFlowOrdersUseCase` (flussi, R1.5.4)
  passano `MarginMode.per_position()`.
- **Adapter** `HyperliquidOrderExchangeAdapter`: `update_leverage(leverage, coin, margin is MarginMode.CROSS)`, cioè
  `is_cross=False` per le posizioni della piattaforma.
- **Scenario** R0.3.1 «Apertura riuscita»: la posizione ha margine isolato.

## Confronto con le decisioni scritte

- `docs/architecture.md:178` (`isolated=True`): rispettata, era lo scostamento.
- `docs/requirements.md` RF-03.03 (flussi isolati anche sullo stesso conto): rafforzata, ora anche dall'exchange.
- CLAUDE.md, regola delle dipendenze: la regola sta nel dominio, la traduzione nell'adapter; nessuna libreria fuori
  dalla sua cartella.
- Scostamenti: nessuno.

## Conseguenze

- **Margine per posizione (ADR 0067)**: la decisione resta, si usa il margine che l'exchange dichiara per ogni
  posizione (`marginUsed`). Con margine isolato è il margine assegnato a quella posizione; il contesto di ADR 0067 sul
  margine ricalcolato al prezzo corrente riguardava il cross. Il margine dell'esecuzione di apertura nello storico
  (dimensione × prezzo medio / leva) coincide con il margine isolato assegnato all'apertura.
- **Margine disponibile**: il conto dichiara come disponibile (`withdrawable`) solo ciò che non è assegnato alle
  posizioni isolate, quindi la liquidità del flusso limitata dal margine libero del conto (ADR 0062) resta corretta.
- **Procedura di verifica (ADR 0079)**: il margine richiesto (valore / leva) è proprio il margine isolato della
  posizione di prova.
- **Liquidazione**: riguarda una sola posizione; l'attribuzione delle esecuzioni di liquidazione al flusso non cambia.
- **Posizione già aperta in cross sullo stesso asset** (per esempio aperta a mano prima di questa decisione):
  Hyperliquid rifiuta il cambio di modo finché è aperta; il rifiuto è un esito dell'ordine con il messaggio
  dell'exchange (R0.3.3), come ogni altro rifiuto della leva. Nessun tentativo automatico.

## Alternative scartate

- **Lasciare il cross e affidare l'isolamento alla sola contabilità della piattaforma**: contraddice
  `docs/architecture.md:178` e lascia che una posizione in perdita usi la garanzia di altri flussi.
- **Margine isolato scelto dall'adapter senza passare dalla porta**: è una regola di business (isolamento tra
  flussi) e deve stare nel dominio, non cablata nella tecnologia.
