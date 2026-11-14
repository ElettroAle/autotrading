# language: it
@R2.3.5
Funzionalità: R2.3.5 Versioni della configurazione a confronto
  Come utente
  Voglio vedere le versioni della configurazione di un flusso e confrontarne due
  Perché capisca che cosa è cambiato quando il rendimento è cambiato

  La dashboard elenca le versioni della configurazione del flusso con data, ora e numero (R1.1.3). L'utente
  sceglie due versioni e le vede affiancate: i campi cambiati sono evidenziati con il valore prima e dopo
  (RF-23.12).

  Fuori ambito: il ripristino di una versione precedente.

  Contesto:
    Dato che il flusso "alfa" ha 3 versioni e tra la 2 e la 3 è cambiato solo il modello da "openrouter/deepseek-chat" a "anthropic/claude-haiku"

  Scenario: Elenco delle versioni
    Quando "anna" apre le versioni del flusso "alfa"
    Allora vede le versioni 3, 2 e 1 con data e ora

  Scenario: Confronto di due versioni
    Quando "anna" confronta le versioni 2 e 3
    Allora le vede affiancate con evidenziato solo il modello, da "openrouter/deepseek-chat" a "anthropic/claude-haiku"

  Scenario: Nessuna differenza
    Quando "anna" confronta la versione 3 con sé stessa
    Allora la dashboard mostra "Nessuna differenza"
