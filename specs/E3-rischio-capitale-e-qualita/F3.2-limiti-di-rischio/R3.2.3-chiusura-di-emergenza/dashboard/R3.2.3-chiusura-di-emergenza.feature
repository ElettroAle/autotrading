# language: it
@R3.2.3
Funzionalità: R3.2.3 Chiusura di emergenza
  Come utente
  Voglio chiudere con un solo comando tutte le posizioni di un flusso, di un conto o di tutti i miei flussi
  Perché in una situazione critica esco subito dal mercato senza agire flusso per flusso

  Il comando si lancia dall'interfaccia programmatica e dalla dashboard, con uno di tre ambiti: un flusso, un
  conto (tutti i suoi flussi), tutti i flussi dell'utente (RF-18.09, RF-21.07, RF-23.13).
  Per ogni flusso dell'ambito la piattaforma chiude a mercato tutte le posizioni, annulla gli ordini di protezione
  (R3.1.2) e mette il flusso in pausa con il motivo "chiusura di emergenza". Un flusso già in pausa resta in pausa e
  le sue posizioni si chiudono. I flussi fermi o archiviati non hanno posizioni e non vengono toccati.
  Le posizioni che nessun flusso possiede non vengono toccate (R1.6.2).
  Una chiusura che fallisce non ferma le altre: l'esito elenca, per flusso, le posizioni chiuse e quelle non chiuse
  con il motivo. Il flusso va in pausa anche se una sua chiusura è fallita.
  Ogni chiusura entra nello storico delle posizioni chiuse con il motivo "chiusura di emergenza". Il comando si
  registra con data, ora, ambito ed esito.
  La dashboard chiede una conferma che nomina l'ambito e il numero di posizioni da chiudere.
  Nella dashboard il comando sta da solo nel riquadro "Zona di emergenza", in fondo alla pagina dei conti e della
  pagina "Generale" delle impostazioni, lontano dagli altri comandi (Bug 545); l'elenco dei flussi, la pagina d'uso
  quotidiano, non lo offre (Bug 563). La chiusura di emergenza di un flusso sta nel riquadro "Zona pericolosa" in
  fondo alla pagina Impostazioni del flusso, con Archivia, e non nella pagina del flusso (Bug 560).
  I flussi riprendono solo per comando dell'utente (R1.1.4).
  Fuori ambito: la procedura di verifica dell'esecuzione, già disponibile (R0.4.1).

  Contesto:
    Dato che "anna" ha sul conto "test-1" i flussi attivi "alfa" con una posizione su "BTC" e "beta" con una posizione su "ETH"
    E che "anna" ha sul conto "test-2" il flusso attivo "gamma" con una posizione su "SOL"

  Scenario: Conferma nella dashboard
    Quando "anna" sceglie nella dashboard la chiusura di emergenza del conto "test-1"
    Allora la dashboard chiede conferma con "Chiudere 2 posizioni dei flussi del conto test-1 e metterli in pausa?"
    E nessuna posizione viene chiusa finché "anna" non conferma

  Scenario: Zona pericolosa in fondo alle impostazioni del flusso
    Quando "anna" apre nella dashboard le impostazioni del flusso "alfa"
    Allora la chiusura di emergenza del flusso "alfa" sta nel riquadro "Zona pericolosa" in fondo alla pagina
    E la pagina del flusso "alfa" non contiene la chiusura di emergenza

  Scenario: Zona di emergenza in fondo alla pagina dei conti
    Quando "anna" apre nella dashboard la pagina dei conti
    Allora il riquadro "Zona di emergenza" in fondo alla pagina contiene la chiusura di emergenza dei conti "test-1" e "test-2"
    E i comandi dei conti non contengono la chiusura di emergenza

  Scenario: Zona di emergenza nelle impostazioni generali
    Quando "anna" apre nella dashboard le impostazioni generali
    Allora la chiusura di emergenza di tutti i flussi sta nel riquadro "Zona di emergenza" in fondo alla pagina
    E il riquadro "Zona di emergenza" non contiene altri comandi
    E l'elenco dei flussi non contiene la chiusura di emergenza

  Scenario: Conferma dalla zona pericolosa
    Quando "anna" sceglie la chiusura di emergenza del flusso "alfa" nel riquadro "Zona pericolosa"
    Allora la dashboard chiede conferma con "Chiudere 1 posizione del flusso alfa e metterlo in pausa?"
    E nessuna posizione viene chiusa finché "anna" non conferma
