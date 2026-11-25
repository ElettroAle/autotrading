# language: it
@R5.3.5
Funzionalità: R5.3.5 Memoria del flusso: miglioramenti
  Come utente
  Voglio che la memoria del flusso dia all'agente il motivo di ogni decisione, come e dopo quanto si sono chiuse le sue
  posizioni e solo le decisioni che contano
  Perché l'agente riconosca una tesi che sta fallendo

  Seguito di R5.3.4. Caso reale: 12 long di fila sullo stesso asset, 11 chiusi in perdita entro pochi minuti, ripetendo
  la stessa tesi.

  Motivo della decisione in una frase. Nella risposta del modello ogni decisione (apri, chiudi, inverti, aggiorna,
  mantieni) porta un motivo in una frase, separato dal ragionamento completo: per un'apertura o un'inversione la tesi,
  per una chiusura il fatto o il livello che l'ha causata, per un aggiornamento cosa cambia e perché, per mantieni cosa
  l'agente aspetta. In memoria entrano il motivo e, per aperture e inversioni, l'invalidazione dichiarata. Il
  ragionamento completo resta nel registro del ciclo e non entra in memoria. Una decisione registrata prima di questo
  cambiamento, senza motivo, entra in memoria con l'inizio del suo ragionamento.

  Lunghezza del testo in memoria: impostazione della memoria, lunghezza massima del motivo per ogni decisione ricordata,
  in caratteri. Predefinito 160; un intero positivo o «illimitata». Un testo più lungo viene tagliato e chiuso con «…»;
  con «illimitata» entra intero.

  Motivo e durata delle chiusure. L'esito di un'apertura in memoria dice anche come si è chiusa la posizione (decisione
  dell'agente, stop loss, take profit, liquidazione o qualunque altro motivo registrato) e dopo quanto tempo
  dall'apertura. Una posizione ancora aperta dice da quanto tempo è aperta. Esempio: «apri long, prezzo 0,002452, chiusa
  dallo stop loss dopo 12 minuti, PnL realizzato -2,32: <motivo>».

  Quali decisioni entrano in memoria: impostazione «tutte le decisioni», spenta di base. Spenta: solo aperture, chiusure
  e inversioni; aggiornamenti e mantieni non entrano e non contano nel numero. Accesa: tutte le decisioni del flusso
  sull'asset, e contano tutte.

  Le nuove impostazioni si impostano come le altre parti della memoria: dashboard, API, strumenti MCP, esportazione e
  importazione della strategia, differenze tra le versioni della configurazione.

  Scenario: Memoria letta dagli strumenti come la riceve l'agente
    Dato che il flusso "alfa" ha la memoria attiva
    E che una posizione aperta da "alfa" su "BTC" è stata chiusa dallo stop loss 12 minuti dopo l'apertura
    Quando il client MCP di "anna" legge la memoria di "alfa"
    Allora riceve per "BTC" le voci come le riceve l'agente
    E le voci sono quelle che risponde l'API
