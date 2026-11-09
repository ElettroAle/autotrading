# language: it
@R0.2.6 @wip
Funzionalità: R0.2.6 Rotazione della chiave di cifratura delle credenziali
  Come proprietario della piattaforma
  Voglio che la chiave che cifra le credenziali dei conti si rinnovi ogni 90 giorni e su mia richiesta
  Perché una chiave vecchia o compromessa non esponga a lungo le credenziali salvate

  La rotazione la esegue la pipeline; in prod parte solo con l'approvazione del proprietario.
  Nessuna persona vede mai la chiave, né la vecchia né la nuova.
  Requisito futuro: non pianificato in E0.

  Fuori ambito: rotazione delle chiavi API sull'exchange (R0.2.4), rotazione dei segreti dei servizi.

  Contesto:
    Dato che l'installazione ha i conti "test-1" e "test-2" con credenziali cifrate con la chiave "A"

  Scenario: Rotazione periodica
    Dato che la chiave "A" è in uso da 90 giorni
    Quando la pipeline esegue la rotazione periodica
    Allora le credenziali dei conti "test-1" e "test-2" sono cifrate con una chiave nuova
    E la chiave "A" è eliminata dall'installazione
    E i conti "test-1" e "test-2" continuano a operare sull'exchange

  Scenario: Rotazione su richiesta
    Quando il proprietario avvia la rotazione dalla pipeline
    Allora le credenziali dei conti "test-1" e "test-2" sono cifrate con una chiave nuova
    E la chiave "A" è eliminata dall'installazione

  Scenario: In prod la rotazione attende l'approvazione
    Quando la rotazione periodica di prod è pronta a partire
    Allora la rotazione attende l'approvazione del proprietario
    E le credenziali restano cifrate con la chiave "A"

  Scenario: Una rotazione incompleta non perde credenziali
    Dato che la nuova cifratura delle credenziali del conto "test-2" fallisce
    Quando la rotazione termina
    Allora la rotazione è segnalata come fallita con il motivo "credenziali non ricifrate: test-2"
    E la chiave "A" resta nell'installazione
    E i conti "test-1" e "test-2" continuano a operare sull'exchange

  Scenario: La chiave non compare nei registri
    Quando la pipeline esegue la rotazione
    Allora nessun registro della pipeline contiene la chiave "A" né la chiave nuova
