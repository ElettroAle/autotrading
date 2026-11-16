# ADR firmatario-autorizzato-per-l-indirizzo-del-conto — Firmatario autorizzato proprio per l'indirizzo del conto Hyperliquid

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 399 (Task 400), R0.2.1, R0.2.4
- Collegate: ADR 0018 (ne supera la sola parte «verifica su Hyperliquid»: la prova firmata resta, non basta più da
  sola), ADR credenziali-senza-caratteri-invisibili-e-forma-diagnosticabile, ADR saldo-dalla-modalita-del-conto-hyperliquid

## Contesto e problema

L'ADR 0018 prova le credenziali firmando con la chiave dell'API wallet un `cancelByCloid` di un `cloid` casuale, e
assume che l'exchange risponda `status: ok` solo a un firmatario autorizzato per il conto. Non è così: Hyperliquid
ricava il conto dal firmatario (un API wallet agisce per il conto che lo ha approvato, un conto per sé stesso) e ignora
l'indirizzo che la richiesta nomina. In dev un conto è stato registrato con l'indirizzo dell'API wallet al posto di
quello del conto: la prova è passata, il worker legge 0 USDC su quell'indirizzo e 999 su quello vero.

## Fattori decisionali

- Registrazione, sostituzione e verifica rifiutano credenziali che non operano sul conto indicato.
- Il motivo del rifiuto è chiaro per l'utente e non contiene alcun carattere del segreto.
- Solo informazioni pubbliche dell'exchange, nessuna azione in più sul conto.

## Opzioni considerate

### 1. Dopo la prova firmata, il ruolo del firmatario (`userRole`) lega il firmatario all'indirizzo

- Firmatario uguale all'indirizzo del conto: accettato se il suo ruolo non è `agent` (un conto firma per sé).
- Firmatario diverso: accettato solo se il suo ruolo è `agent` e `data.user` è l'indirizzo del conto, senza badare a
  maiuscole e minuscole.
- Altrimenti rifiuto con un motivo nostro: «l'indirizzo del conto è quello dell'API wallet: va indicato l'indirizzo del
  conto che lo ha approvato» oppure «l'API wallet non è autorizzato per l'indirizzo del conto».
- Buona: una lettura pubblica in più, prova esatta del legame. Cattiva: una richiesta in più a ogni lettura dello stato.

### 2. Confrontare il saldo letto con quello atteso

- Cattiva: un conto vuoto è legittimo; non dice nulla del legame tra chiave e indirizzo.

### 3. Chiedere all'exchange l'elenco degli API wallet del conto (`extraAgents`)

- Cattiva: non copre il conto che firma per sé e gli API wallet senza nome; `userRole` risponde dal lato del firmatario
  in una sola lettura.

## Esito della decisione

Opzione 1, in `HyperliquidExchangeAdapter.read_state`, che serve registrazione, sostituzione, verifica e ciclo (e quindi
anche la sottoclasse di test). La prova firmata resta: dice che la chiave è nota all'exchange. Un ruolo di forma
inattesa o non letto rende l'exchange non disponibile, mai un'autorizzazione presunta.

### Conseguenze

- Un conto registrato con l'indirizzo dell'API wallet o con un API wallet di un altro conto è rifiutato prima di
  leggere il saldo; i conti già registrati così falliscono alla prossima lettura e vanno sostituiti con l'indirizzo
  giusto.
- Un API wallet revocato o scaduto smette di leggere il conto, con lo stesso motivo.
- Una richiesta in più (`userRole`) per ogni lettura dello stato del conto.
