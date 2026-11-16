# language: it
@R6.4.4
Funzionalità: R6.4.4 Tabelle leggibili e filtrabili
  Come utente
  Voglio tabelle che stanno nello schermo e che posso filtrare
  Perché trovo subito i cicli o le posizioni che mi interessano, anche dal telefono

  Vale per tutte le tabelle della dashboard, attraverso il componente tabella condiviso. Una tabella non allarga
  mai la pagina: su schermi stretti ogni riga diventa una scheda; su schermi larghi, se le colonne non stanno, la
  tabella scorre al proprio interno con la prima colonna fissa. Quando una riga porta a un dettaglio, tutta la riga
  è cliccabile e lo mostra. Ogni tabella dichiara i propri filtri, mostrati sopra la tabella come scelte rapide,
  con il conteggio dei risultati e il comando per azzerarli; i filtri stanno nell'indirizzo della pagina. Filtri:
  cicli per esito (tutti, conclusi, falliti) e per decisione (apertura, chiusura, mantenimento, nessuna); posizioni
  chiuse per direzione (long, short), risultato (vinte, perse) e asset. La classifica dei flussi resta nello
  schermo come le altre tabelle.

  Scenario: Cicli filtrati per esito
    Dato che il flusso "alfa" ha 38 cicli conclusi e 2 falliti
    Quando "anna" filtra i cicli del flusso sui falliti
    Allora vede 2 cicli, tutti falliti, e il conteggio "2 cicli"

  Scenario: Cicli filtrati per decisione
    Dato che il flusso "alfa" ha 3 cicli con un'apertura
    Quando "anna" filtra i cicli del flusso sulle aperture
    Allora vede 3 cicli, tutti con un'apertura

  Scenario: Posizioni chiuse filtrate
    Dato che il flusso "alfa" ha 2 posizioni chiuse short vinte e 1 long persa
    Quando "anna" filtra le posizioni chiuse sulle perse
    Allora vede solo la posizione long persa

  Scenario: Azzerare i filtri
    Dato che "anna" ha filtrato i cicli sui falliti
    Quando azzera i filtri
    Allora vede tutti i cicli del periodo

  Scenario: Riga cliccabile
    Quando "anna" sceglie un punto qualsiasi della riga di un ciclo
    Allora vede il dettaglio di quel ciclo

  Scenario: Tabelle nello schermo
    Dato uno schermo largo 360 pixel e uno largo 900 pixel
    Quando "anna" apre posizioni chiuse, cicli e classifica dei flussi
    Allora nessuna pagina scorre in orizzontale

  Scenario: Filtri nell'indirizzo
    Dato che "anna" ha filtrato le posizioni chiuse sulle short
    Quando ricarica la pagina
    Allora il filtro sulle short è ancora attivo
