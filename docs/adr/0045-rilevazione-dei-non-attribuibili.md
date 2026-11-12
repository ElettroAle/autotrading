# ADR 0045 — Rilevazione di posizioni e movimenti non attribuibili

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.2 (Task T1.6.2.1)

## Contesto

A ogni ciclo di un flusso, la piattaforma cerca sul conto ciò che nessun flusso spiega:

- una posizione su un asset di nessun flusso;
- una posizione di un flusso sparita dall'exchange senza un suo ordine;
- un'esecuzione senza identificativo della piattaforma;
- una variazione del saldo non spiegata (deposito, prelievo).

Ogni caso si registra una volta sola e si notifica (R1.8.2), senza toccare l'exchange e senza fermare i flussi.
Una posizione chiusa fuori dalla piattaforma entra nello storico del flusso con il motivo "chiusa fuori dalla
piattaforma". Lo stato si ricava dall'exchange (ADR 0044).

## Decisione

- **Domain** (`flows`): `AccountReconciliation.of` confronta la lettura del conto con la lettura precedente
  (`AccountReading`: istante e asset aperti di ogni flusso) e dà:
  - posizioni su asset che nessun flusso non archiviato del conto possiede;
  - esecuzioni successive alla lettura precedente il cui `cloid` manca o non è di un ordine della piattaforma;
  - movimenti del saldo successivi alla lettura precedente;
  - `OutsideClosing` per ogni asset aperto di un flusso alla lettura precedente che ora non c'è più, quando nessuna
    esecuzione di un ordine di quel flusso su quell'asset lo spiega. L'esito (PnL realizzato, commissioni, istante)
    viene dalle esecuzioni fuori piattaforma su quell'asset, per esempio una liquidazione.
  Senza una lettura precedente, esecuzioni e movimenti passati sono il punto di partenza e non si segnalano.
- **Variazione del saldo dai movimenti dell'exchange**: un movimento è un aggiornamento del registro che non riguarda
  il funding (deposito, prelievo, trasferimento interno, tra sottoconti, tra spot e perpetui), con il suo segno. La
  differenza dei saldi, invece, conterrebbe funding e PnL non realizzato, cioè una segnalazione falsa a ogni ciclo.
- **Una sola registrazione**: `ReconciliationRepositoryPort.record` restituisce vero solo per un caso nuovo. Il
  caso è identificato da conto, tipo e riferimento (asset della posizione, `tid` dell'esecuzione, hash del
  movimento), con un indice unico parziale sui casi non risolti. Una posizione registrata che non è più aperta si
  risolve, così una nuova posizione sullo stesso asset è un caso nuovo. Due cicli dello stesso conto in parallelo non
  registrano due volte.
- **Caso d'uso** `ReconcileAccountUseCase(flusso)`:
  1. legge flussi, attività, ordini e lettura precedente;
  2. registra i casi;
  3. risolve le posizioni chiuse;
  4. passa le chiusure fuori piattaforma a `ClosedPositionsPort`;
  5. salva la nuova lettura;
  6. restituisce i casi nuovi e le chiusure, perché il ciclo li notifichi (R1.8.2).
- **Persistenza**: migrazione `0010` con `account_readings` (una riga per conto) e `unattributable_items`, entrambe
  sotto RLS per tenant e con il conto legato al tenant. Le righe dei casi non si cancellano: si risolvono.

## Alternative scartate

- **Differenza dei saldi tra due letture**: funding e PnL non realizzato cambiano il saldo a ogni ciclo senza alcun
  movimento.
- **Posizioni "aperte per la piattaforma" ricostruite dagli ordini**: con chiusure parziali e liquidazioni il
  conteggio diverge da ciò che l'exchange mostra; la lettura precedente è un fatto dell'exchange.
- **Registrazione senza risoluzione**: una posizione chiusa e riaperta sullo stesso asset non verrebbe più
  segnalata.

## Conseguenze

- Il ciclo (F1.2) chiama il caso d'uso e notifica i casi nuovi: il collegamento in `bootstrap.py` arriva con
  l'integrazione dei cicli.
- `ClosedPositionsPort` si collega allo storico delle posizioni chiuse di R1.7.2, che conserva i campi completi della
  posizione; fino ad allora nessun adapter reale la implementa.
- Gli aggiornamenti del registro di altri tipi (vault, staking) non sono movimenti del saldo dei perpetui e non si
  segnalano.
