# language: it
@R5.1.5
Funzionalità: R5.1.5 Forecast su orizzonti lunghi
  Come utente
  Voglio previsioni a giorni e settimane
  Perché un agente strategico ragiona su finestre lunghe

  La fonte "forecast" accetta come orizzonti anche 1 giorno e 1 settimana, oltre a 15 minuti e 1 ora (RF-08.05).
  Gli orizzonti lunghi si calcolano su candele giornaliere; ogni previsione si registra e riceve il prezzo
  effettivo allo scadere, come oggi, e partecipa alla valutazione del forecast (RF-26.01) e al grafico (R4.3.1).
  Lo storico più corto della profondità richiesta si dichiara.

  Contesto:
    Dato che il flusso "alfa" ha la fonte "forecast" sull'asset "BTC"

  Scenario: Orizzonte non ammesso
    Quando "anna" imposta l'orizzonte "3 mesi"
    Allora la configurazione è rifiutata con il motivo che elenca gli orizzonti ammessi
