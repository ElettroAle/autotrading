# language: it
@R2.3.10
Funzionalità: R2.3.10 Avviso della rete di test
  Come utente
  Voglio vedere con chiarezza quando un conto o un flusso opera sulla rete di test di un exchange
  Perché non scambi risultati senza denaro reale per risultati veri, né il contrario

  La rete e il suo nome li dichiara l'adapter dell'exchange; la dashboard non conosce alcun exchange e mostra ciò
  che l'API restituisce. Rete di test: avviso giallo; rete reale: avviso rosso.

  La rete si sceglie scegliendo l'exchange alla registrazione del conto (R2.3.11).

  Contesto:
    Dato che "anna" è nella pagina dei conti

  Scenario: La registrazione mostra che l'exchange opera sulla rete di test
    Dato che l'exchange "Hyperliquid" è configurato sulla rete di test "testnet"
    Quando "anna" sceglie l'exchange "Hyperliquid" per registrare un conto
    Allora la registrazione avvisa che il conto opererà sulla rete di test "testnet" senza denaro reale

  Scenario: Il conto dichiara la sua rete nell'elenco e nel dettaglio
    Dato che "anna" ha il conto "test-1" su un exchange configurato sulla rete di test "testnet"
    Quando "anna" apre i suoi conti
    Allora il conto "test-1" è segnato come rete di test "testnet"

  Scenario: Il conto su rete reale è segnato come reale
    Dato che "anna" ha il conto "vero-1" su un exchange configurato sulla rete reale
    Quando "anna" apre i suoi conti
    Allora il conto "vero-1" è segnato come rete reale

  Scenario: Il flusso su rete di test lo dichiara
    Dato che il flusso "epsilon" è assegnato a un conto sulla rete di test "testnet"
    Quando "anna" apre il flusso "epsilon"
    Allora la pagina avvisa che il flusso opera sulla rete di test "testnet" senza denaro reale

  Scenario: Il flusso su rete reale non mostra l'avviso di test
    Dato che il flusso "delta" è assegnato a un conto sulla rete reale
    Quando "anna" apre il flusso "delta"
    Allora la pagina non mostra l'avviso della rete di test
