# ADR variazioni-sotto-soglia-senza-notifica — Una variazione del saldo entro la soglia si registra senza notifica

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 596, Task 599; R1.6.2, R1.8.2, R3.3.1
- Collegate: ADR 0045 (rilevazione dei non attribuibili), ADR allarme-di-riconciliazione-sul-saldo-del-conto, ADR
  saldo-atteso-con-le-sole-righe-successive-alla-lettura-precedente
- Verifica: prova

## Contesto e problema

`NotifyUnattributableUseCase` notifica ogni caso nuovo, anche ogni `BALANCE_CHANGE`: la riconciliazione gira
all'inizio e alla fine di ogni ciclo di ogni flusso del conto e ogni confronto con una differenza diversa da zero è un
caso a sé. Decine di notifiche di pochi centesimi in pochi minuti (dev, 17/11/2026).

## Fattori decisionali

- Decisione del proprietario (17/11/2026): si notifica solo oltre la soglia del conto; le variazioni entro la soglia
  si registrano e si vedono nella dashboard (Bug 596, Task 600).
- R3.3.1: entro la soglia la variazione si registra come non spiegata, senza allarme.
- Le posizioni e le esecuzioni non attribuibili restano notificate (R1.6.2; diventano avvisi in R6.2.3).

## Decisione

- `NotifyUnattributableUseCase` non notifica più i casi `BALANCE_CHANGE`: la regola sta nel domain
  (`UnattributableKind.told`, vero per posizione ed esecuzione) e il caso d'uso filtra con quella. La registrazione in
  `ReconcileAccountUseCase` non cambia.
- `UnattributableMovementNoticePort`, il suo adapter di notifica e il genere di notifica del movimento non
  attribuibile si rimuovono con le loro prove, insieme al link «Apri allarmi» di quel genere (nessun codice morto).
- Specifiche: R1.6.2, R1.8.2 e R3.3.1 dicono che la variazione entro la soglia non si notifica; lo scenario «Variazione
  del saldo non spiegata» aggiunge «E "anna" non riceve alcuna notifica». Board riallineata.
- Prove: unit test del domain e del caso d'uso; scenari R1.6.2 e R3.3.1 aggiornati.

## Alternative scartate

- Importo minimo sotto cui non notificare: scartata dal proprietario.
- Un solo riassunto periodico delle variazioni: le variazioni si consultano nel conto.

## Conseguenze

- Su Telegram e email arrivano solo i casi che chiedono attenzione; le variazioni piccole restano nel registro del
  conto.
