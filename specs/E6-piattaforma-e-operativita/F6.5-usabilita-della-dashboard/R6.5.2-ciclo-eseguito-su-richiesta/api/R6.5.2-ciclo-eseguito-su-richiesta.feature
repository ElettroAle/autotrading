# language: it
@R6.5.2
Funzionalità: R6.5.2 Ciclo eseguito su richiesta
  Come utente
  Voglio eseguire subito un ciclo del flusso con un pulsante
  Perché posso vedere la decisione dell'agente senza aspettare l'orario pianificato

  Per un flusso attivo la pagina del flusso ha il comando «Esegui ora», disponibile anche dall'interfaccia
  programmatica. Il ciclo su richiesta è un ciclo completo come quello pianificato (R1.2.1), lo esegue il worker ed
  è registrato come eseguito su richiesta. Rispetta il divieto di sovrapposizione (R1.2.2): se un ciclo del flusso è
  già in corso il comando è rifiutato con 409 e il motivo. Il ciclo pianificato successivo resta al suo orario. Un
  flusso in pausa o fermo non ha il comando.

  Contesto:
    Dato che "anna" ha il flusso attivo "alfa" con un ciclo ogni 60 minuti, il prossimo alle 11:00

  Scenario: Ciclo su richiesta
    Quando "anna" sceglie «Esegui ora» sul flusso "alfa" alle 10:20
    Allora il worker esegue un ciclo completo di "alfa"
    E il ciclo compare tra i cicli come eseguito su richiesta
    E il ciclo pianificato successivo resta alle 11:00

  Scenario: Ciclo già in corso
    Dato che un ciclo di "alfa" è in corso
    Quando "anna" sceglie «Esegui ora» sul flusso "alfa"
    Allora la richiesta è rifiutata con stato 409 e il motivo "un ciclo del flusso è già in corso"
    E non parte un secondo ciclo

  Schema dello scenario: Flusso non attivo
    Dato che il flusso "alfa" è <stato>
    Quando "anna" apre la pagina del flusso "alfa"
    Allora non vede il comando «Esegui ora»
    E la richiesta dall'interfaccia programmatica è rifiutata con il motivo "il flusso non è attivo"

    Esempi:
      | stato    |
      | in pausa |
      | fermo    |
