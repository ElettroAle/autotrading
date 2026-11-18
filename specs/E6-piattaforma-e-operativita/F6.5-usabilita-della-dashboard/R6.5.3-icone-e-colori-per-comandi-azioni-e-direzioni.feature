# language: it
@R6.5.3
Funzionalità: R6.5.3 Icone e colori per comandi, azioni e direzioni
  Come utente
  Voglio riconoscere a colpo d'occhio comandi, azioni e direzioni
  Perché la dashboard sia più intuitiva e non debba leggere ogni etichetta

  I comandi di stato del flusso hanno colore e icona propri: Pausa ambra con l'icona pausa, Riprendi verde con
  l'icona play, Stop rosso con l'icona quadrato, Avvia verde con l'icona play. Le direzioni hanno un'icona (long
  freccia in su, short freccia in giù) e così le azioni dell'agente (apri, chiudi, mantieni, aggiorna, inverti)
  ovunque compaiano: cicli, decisioni, posizioni aperte e chiuse. L'icona accompagna sempre il testo, non lo
  sostituisce, e ha un nome accessibile; il colore non è l'unico segno.
  Le icone vengono dalla libreria lucide-react, da dichiarare in .claude/rules/tech-dashboard.md; comandi, azioni e
  direzioni usano componenti condivisi, non icone sparse nelle funzionalità.

  Contesto:
    Dato che "anna" ha il flusso attivo "alfa" con posizioni e cicli

  Schema dello scenario: Comandi di stato riconoscibili
    Quando "anna" apre la pagina di un flusso in cui è disponibile il comando <comando>
    Allora il comando <comando> è <colore> con l'icona <icona> e il testo "<comando>"

    Esempi:
      | comando  | colore | icona    |
      | Pausa    | ambra  | pausa    |
      | Riprendi | verde  | play     |
      | Stop     | rosso  | quadrato |

  Schema dello scenario: Direzioni e azioni con icona
    Quando "anna" guarda una decisione o una posizione con <valore>
    Allora accanto al testo "<valore>" vede l'icona <icona>

    Esempi:
      | valore   | icona            |
      | long     | freccia in su    |
      | short    | freccia in giù   |
      | apri     | più              |
      | chiudi   | x                |
      | mantieni | pausa            |
      | aggiorna | frecce circolari |

  Scenario: Icone accessibili
    Quando un lettore di schermo legge un comando, un'azione o una direzione
    Allora legge il suo nome e non il nome dell'icona
