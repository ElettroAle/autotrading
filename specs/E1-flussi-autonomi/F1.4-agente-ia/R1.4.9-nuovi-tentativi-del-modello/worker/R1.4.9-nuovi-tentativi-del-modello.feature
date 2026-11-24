# language: it
@R1.4.9
Funzionalità: R1.4.9 Nuovi tentativi della chiamata al modello
  Come utente
  Voglio che un errore temporaneo del fornitore IA sia ritentato dentro il ciclo
  Perché un disservizio di pochi secondi non mi fa perdere la decisione di un intero ciclo

  Se la chiamata al modello fallisce con un errore temporaneo (lo decide l'errore base: 429, 5xx, tempo scaduto, rete),
  la decisione la ritenta fino a 3 volte, con attese di 2, 8 e 30 secondi. Se un tentativo riesce, il ciclo prosegue.
  Esauriti i tentativi, il ciclo fallisce come in R1.2.3. Un errore permanente non si ritenta (R1.2.4). Il costo di
  ogni tentativo che ne ha uno e il numero dei tentativi sono registrati nel ciclo.

  Una risposta che il modello non finisce perché esaurisce il limite di token del flusso è un errore temporaneo come gli
  altri (Bug 733): si ritenta allo stesso modo, e se si interrompe in ogni tentativo il motivo dice il limite e il
  rimedio, non un fornitore irraggiungibile.

  Fuori ambito: nuovi tentativi degli altri passi del ciclo; una risposta arrivata ma non conforme (R1.4.5).

  Contesto:
    Dato che "anna" ha il flusso attivo "alfa"

  Scenario: Errore temporaneo poi riuscita
    Dato che il fornitore IA risponde 503 alla prima chiamata e una decisione valida alla seconda
    Quando parte il ciclo di "alfa"
    Allora la chiamata è ritentata dopo 2 secondi
    E il ciclo prosegue con la decisione
    E il ciclo registra 2 tentativi

  Scenario: Tentativi esauriti
    Dato che il fornitore IA risponde 429 a tutte le chiamate
    Quando parte il ciclo di "alfa"
    Allora la chiamata è ritentata 3 volte, dopo 2, 8 e 30 secondi
    E il ciclo fallisce nel passo dell'agente con il motivo dell'errore, come in R1.2.3
    E il ciclo registra 4 tentativi

  Scenario: Errore permanente
    Dato che il fornitore IA risponde 402 credito esaurito
    Quando parte il ciclo di "alfa"
    Allora la chiamata non è ritentata
    E il ciclo fallisce e il flusso va in pausa come in R1.2.4

  Scenario: Costo dei tentativi
    Dato che il primo tentativo ha risposto 500 con un costo di 0,001 USD e il secondo una decisione con 0,004 USD
    Quando il ciclo di "alfa" si conclude
    Allora il costo del ciclo è 0,005 USD

  Scenario: Risposta interrotta in ogni tentativo
    Dato un flusso "alfa" con max_tokens 4096
    E che il modello esaurisce i 4096 token prima di finire la risposta in ogni tentativo
    Quando parte un ciclo di "alfa"
    Allora il ciclo fallisce con il motivo "risposta del modello interrotta dal limite di 4096 token: alza max_tokens o abbassa il ragionamento del flusso"
    E il motivo non dice "fornitore IA non raggiungibile"
    E il ciclo registra il costo e i tentativi delle chiamate interrotte

  Scenario: Risposta interrotta al primo tentativo e completa al secondo
    Dato che il modello esaurisce i token solo al primo tentativo
    Quando parte un ciclo di "alfa"
    Allora il ciclo è concluso con 2 tentativi del modello
