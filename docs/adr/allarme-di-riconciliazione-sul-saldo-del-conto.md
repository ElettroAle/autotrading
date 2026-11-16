# ADR allarme-di-riconciliazione-sul-saldo-del-conto — Allarme di riconciliazione sul saldo del conto

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.3.1 (462), Task T3.3.1.1 (485)
- Collegate: ADR 0056 e 0063 (riconciliazione e registro delle esecuzioni, R1.6.2), ADR 0078 (stato del rischio),
  ADR permanenza-decisa-dall-errore-base

## Contesto e problema

La riconciliazione di R1.6.2 (`ReconcileAccountUseCase`, `AccountReconciliation`) gira a inizio e fine di ogni ciclo
per il conto del flusso: registra le esecuzioni dei flussi, segnala posizioni, esecuzioni e movimenti del saldo non
attribuibili e salva l'ultima lettura del conto (`AccountReading`). Non confronta il saldo: un intervento manuale o
una liquidazione lasciano i flussi a operare su numeri falsi. Oggi depositi e prelievi dichiarati dall'exchange sono
segnalati come variazioni non attribuibili, mentre R3.3.1 li vuole spiegati.

## Fattori decisionali

- R3.3.1 e decisioni del proprietario (16/11/2026): soglia per conto da 0,1 a 100, 1 se non indicata; un solo allarme
  aperto per conto; depositi e prelievi dichiarati sono spiegati; le aperture di tutti i flussi del conto restano
  sospese fino alla conferma; chiusure, piano di uscita e cicli proseguono.
- CLAUDE.md: niente ponti tra contesti (il contesto che usa un dato dichiara le sue porte), il caso d'uso orchestra,
  gli errori tipizzati dichiarano la risposta.
- Il saldo letto da Hyperliquid (`account_value`) comprende il PnL non realizzato delle posizioni aperte, che nessuna
  esecuzione spiega finché la posizione è aperta.

## Opzioni considerate

1. **Confronto nel dominio della riconciliazione, riferimento salvato con la lettura.**
   - Contesto `accounts`: value object `DeviationThreshold` (da 0,1 a 100, predefinito 1) sull'`Account`; errore
     `DeviationThresholdOutOfRangeError` ("la soglia di scostamento va da 0,1 a 100"); caso d'uso
     `SetDeviationThresholdUseCase`; colonna `deviation_threshold` sui conti (migrazione con default 1).
   - Contesto `flows`: `BalanceComparison` calcola saldo atteso, saldo letto e scostamento in percentuale del saldo
     atteso. Saldo letto = saldo del conto meno il PnL non realizzato delle posizioni lette; saldo atteso = saldo di
     riferimento + somma di `realized_pnl - fee` delle esecuzioni registrate nella riconciliazione + funding
     registrato + movimenti dichiarati dall'exchange dopo la lettura precedente. `RecordAccountExecutionsUseCase`
     restituisce anche i pagamenti di funding registrati.
   - `AccountReading` porta il saldo di riferimento. Entro la soglia il nuovo riferimento è il saldo letto e uno
     scostamento diverso da zero si registra come variazione del saldo non spiegata (`BALANCE_CHANGE`, con
     l'importo); oltre la soglia il nuovo riferimento è il saldo atteso, così lo scostamento resta finché l'utente
     non conferma. La prima lettura del conto fissa il riferimento senza confronto. I movimenti dichiarati non sono
     più elementi non attribuibili.
   - `ReconciliationAlarm` (conto, saldo atteso, saldo letto, scostamento, aperto il, confermato il) nella tabella
     `reconciliation_alarms` con indice unico parziale sugli allarmi aperti del conto: un solo allarme aperto anche
     con due cicli concorrenti. `ReconciliationRepositoryPort` aggiunge `open_alarm(account_id)`, `open(alarm)` (vero
     se nuovo), `confirm(account_id, at)` e l'elenco degli allarmi del conto.
   - `ReconcileAccountUseCase` legge la soglia dalla nuova porta `AccountDeviationThresholdPort` (realizzata
     dall'adapter SQLAlchemy nella sua cartella), apre l'allarme e solo se nuovo avvisa con la porta
     `ReconciliationAlarmNoticePort`, realizzata dal caso d'uso `NotifyReconciliationAlarmUseCase` del contesto
     `notifications` ("test-1: allarme di riconciliazione, saldo 980 USDC invece di 1000 USDC") come le altre
     segnalazioni di R1.6.2.
   - Sospensione: `ReadCycleFlowUseCase` legge l'allarme aperto del conto e lo mette nel `CycleFlow`; `RiskState`
     porta il motivo della sospensione delle aperture e `RiskCheck` blocca ogni apertura con
     `BlockedDecision(asset, "allarme di riconciliazione sul conto test-1")`, registrata nel ciclo come "apertura ETH
     non eseguita: …"; chiusure e piano di uscita non passano dal blocco. La riconciliazione di inizio ciclo precede
     la revisione del rischio, quindi l'allarme aperto in un ciclo blocca già le sue aperture.
   - Conferma: `ConfirmReconciliationUseCase` (flows) chiude l'allarme con data e ora e porta il riferimento al saldo
     letto dell'ultima lettura; senza allarme aperto `ReconciliationAlarmNotOpenError` (409) "il conto test-1 non ha
     un allarme di riconciliazione aperto".
   - API: `PUT /accounts/{account_id}/deviation-threshold`, `GET /accounts/{account_id}/reconciliation` (ultimo
     confronto, soglia, allarme aperto), `GET /accounts/{account_id}/reconciliation/alarms` (dal più recente),
     `POST /accounts/{account_id}/reconciliation/confirmation`.
2. **Confronto su `account_value` senza togliere il PnL non realizzato**: scartata, ogni oscillazione di prezzo di una
   posizione aperta diventerebbe scostamento e aprirebbe allarmi falsi.
3. **Allarme come pausa automatica dei flussi** (R1.2.4): scartata, R3.3.1 vuole i cicli attivi con chiusure e piano
   di uscita eseguiti, e la ripresa legata alla conferma sul conto, non al singolo flusso.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.3.1 sui casi d'uso con adapter finti; unit test di `DeviationThreshold`,
`BalanceComparison`, `RiskCheck` con sospensione e dei casi d'uso; integrazione dell'adapter SQLAlchemy, con l'indice
unico degli allarmi aperti, e della migrazione; test delle rotte API).

### Conseguenze

- Ogni ciclo confronta il saldo del conto; un allarme ferma solo le aperture di quel conto fino alla conferma.
- Depositi e prelievi dichiarati non generano più segnalazioni di variazioni non attribuibili.
- Le esecuzioni non attribuibili a un flusso non sono spiegate: se spostano il saldo oltre la soglia aprono l'allarme,
  oltre a restare segnalate (R1.6.2).
