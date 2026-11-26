# ADR controllo-delle-riaperture-dopo-perdite-consecutive — Controllo delle riaperture dopo perdite consecutive nel
  rischio del ciclo

- Stato: accettata (26 novembre 2026)
- Requisiti: US 754 R5.5.2 (Task 756)
- Collegate: ADR limite-di-perdite-consecutive-del-flusso, ADR 0040 (controllo del rischio), ADR
  chiusure-per-protezione-nello-storico; `.claude/rules/context-flows.md`, `.claude/rules/context-agent.md`,
  `.claude/rules/tech-sqlalchemy.md`
- Verifica: prova

## Contesto e problema

Con il limite impostato, un'apertura in una direzione va bloccata quando le ultime posizioni chiuse in quella direzione
(sull'asset o su tutto il flusso, secondo l'ambito) dentro la finestra sono in perdita per almeno il numero massimo, e
dall'ultima di quelle chiusure non è passata la durata del blocco.

## Fattori decisionali

- Regole di R5.5.2: conteggio dalla più recente all'indietro, interrotto da una chiusura in utile o in pari; perdita =
  PnL al netto delle commissioni sotto zero; il blocco finisce da solo; di un'inversione bloccata si esegue la sola
  chiusura; il blocco in corso arriva all'agente e si vede in API, MCP e dashboard. Motivi letterali dei criteri.
- Il risultato netto di una posizione chiusa è già del domain (`ClosedPosition.net_pnl`, R2.2.6).
- Il controllo del rischio (`RiskCheck`) decide già gli esiti delle intenzioni; l'apertura di un'inversione si controlla
  dopo la chiusura.

## Decisione

- **Regola nel domain.** `ReopeningBlock` (distinto dal limite `ConsecutiveLossLimit` della configurazione) dice, dalle
  posizioni chiuse del flusso (lato, asset, chiusura, risultato netto) e dall'istante, quali blocchi sono in corso: per ogni direzione e, con ambito «asset», per ogni asset; il
  conteggio va dalla chiusura più recente nella finestra all'indietro finché il risultato netto è sotto zero; con
  conteggio ≥ massimo il blocco dura fino all'ultima chiusura contata più la durata. Il blocco ha il suo testo per lo
  stato («riaperture short su NEAR ferme fino alle 15:30: 2 perdite consecutive»; con ambito flusso «riaperture short
  ferme fino alle 15:30: 2 perdite consecutive short nel flusso») e per l'esito
  («apertura short su NEAR bloccata: …»), con l'ora nel fuso dei testi del ciclo.
- **Rischio del ciclo.** `RiskCheck` riceve i blocchi in corso: un'apertura in una direzione bloccata diventa una
  decisione bloccata con il motivo; di un'inversione si approva la chiusura e si blocca l'apertura opposta, e il ciclo
  registra il motivo. Le altre direzioni e gli altri asset non sono toccati.
- **Lettura.** Una porta del contesto `flows` restituisce le posizioni chiuse del flusso dentro la finestra (lettura
  dallo storico delle posizioni chiuse, adapter `sqlalchemy/` sotto RLS); solo i flussi con il limite la leggono.
- **Stato.** `ReadFlowStateUseCase` aggiunge i blocchi in corso allo stato del flusso per API, strumenti MCP e
  dashboard, e lo stato inviato all'agente li riporta; senza limite non c'è nessuna riga.

## Alternative scartate

- **Blocco salvato al momento della perdita**: duplica lo storico e richiede di scadere; calcolato dalle chiusure
  finisce da solo e segue le modifiche del limite.

## Conseguenze

- Una lettura in più delle posizioni chiuse per ciclo, solo per i flussi con il limite.
