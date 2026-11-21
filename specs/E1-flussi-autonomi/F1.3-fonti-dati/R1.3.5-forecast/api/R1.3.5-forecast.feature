# language: it
@R1.3.5
Funzionalità: R1.3.5 Fonte forecast
  Come utente
  Voglio che l'agente riceva una previsione del prezzo di ogni asset a 15 minuti e a 1 ora
  Perché tenga conto della direzione attesa del prezzo nel breve

  Per ogni asset e orizzonte la previsione riporta: ultimo prezzo, prezzo previsto, variazione percentuale
  prevista, orizzonte. Gli orizzonti sono 15 minuti e 1 ora.
  La previsione si calcola sullo storico dei prezzi dell'exchange; la profondità dello storico è un parametro del
  flusso, in giorni da 1 a 90, predefinito 7.
  Ogni previsione si registra; allo scadere dell'orizzonte si registra accanto il prezzo effettivo, per la
  valutazione dell'errore in un'epica successiva.
  Se lo storico disponibile è più corto della profondità richiesta, la previsione usa lo storico disponibile e il
  contesto lo dichiara.

  Fuori ambito: orizzonti di giorni o settimane, la valutazione dell'errore delle previsioni.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC" e la fonte "forecast" attiva

  Schema dello scenario: Profondità dello storico fuori dall'intervallo
    Quando "anna" imposta sul flusso "alfa" la fonte "forecast" con profondità storico giorni <valore>
    Allora la modifica è rifiutata con il motivo "parametro fuori dai valori ammessi: profondità storico giorni, da 1 a 90"

    Esempi:
      | valore |
      | 0      |
      | 91     |
