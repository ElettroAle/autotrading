# language: it
@R1.4.4
Funzionalità: R1.4.4 Decisione dell'agente per ogni asset
  Come utente
  Voglio che l'agente restituisca a ogni ciclo una decisione strutturata per ciascun asset del flusso
  Perché ogni decisione sia eseguibile senza interpretazioni e il suo ragionamento resti visibile

  Per ogni asset la decisione è una tra: apri (long o short), chiudi, mantieni. Ogni decisione contiene il
  ragionamento dell'agente, conservato anche per "mantieni".
  Un'apertura contiene in più: direzione, quota del capitale del flusso da impegnare come margine (frazione da
  0 a 1) e leva. Per "mantieni" e "chiudi" i campi operativi presenti si ignorano.
  La chiusura è sempre totale.

  Fuori ambito: exit plan, confidenza, chiusure parziali; la risposta non conforme (R1.4.5).

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC, ETH, SOL"

  Scenario: Una decisione per ogni asset
    Dato che l'agente risponde apri long su "BTC", chiudi su "ETH" e mantieni su "SOL"
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra le decisioni:
      | asset | azione   |
      | BTC   | apri     |
      | ETH   | chiudi   |
      | SOL   | mantieni |

  Scenario: Apertura con i suoi campi
    Dato che l'agente risponde su "BTC" apri long con quota 0,1, leva 3 e ragionamento "rottura della resistenza"
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra per "BTC" un'apertura long con quota 0,1 e leva 3
    E il ciclo registra per "BTC" il ragionamento "rottura della resistenza"

  Scenario: Mantieni con campi operativi
    Dato che l'agente risponde su "SOL" mantieni con leva 10 e ragionamento "mercato laterale"
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra per "SOL" la decisione mantieni senza campi operativi
    E il ciclo registra per "SOL" il ragionamento "mercato laterale"

  Scenario: Chiusura totale
    Dato che il flusso "alfa" ha una posizione long su "ETH" di 0,5 ETH
    E che l'agente risponde chiudi su "ETH"
    Quando il flusso "alfa" esegue un ciclo
    Allora l'ordine di chiusura su "ETH" riguarda 0,5 ETH
