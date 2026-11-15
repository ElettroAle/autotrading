# language: it
@R2.3.11
Funzionalità: R2.3.11 Exchange di test selezionabile
  Come utente
  Voglio scegliere alla registrazione del conto se opera su Hyperliquid o su Hyperliquid Testnet
  Perché la rete del conto si capisca dall'exchange che scelgo, senza dipendere da come è configurata l'installazione

  Ogni installazione offre sempre entrambi gli exchange; nessuna impostazione dell'installazione sceglie la rete.
  L'exchange di test è un adapter dedicato che eredita da quello reale e ne cambia solo rete e indirizzo dell'API.
  L'avviso della rete di test e la conferma del denaro reale seguono l'exchange del conto (R2.3.10, R2.3.4).

  Scenario: Ogni installazione offre l'exchange reale e quello di test
    Dato un'installazione senza alcuna impostazione della rete di Hyperliquid
    Quando "anna" chiede gli exchange supportati
    Allora gli exchange sono "Hyperliquid" sulla rete reale "mainnet" e "Hyperliquid Testnet" sulla rete di test "testnet"

  Scenario: Un conto su Hyperliquid Testnet opera sulla testnet in ogni suo uso
    Dato un'installazione senza alcuna impostazione della rete di Hyperliquid
    Quando un conto dichiara l'exchange "Hyperliquid Testnet"
    Allora lettura del conto, mercati, ordini, attività ed esecuzioni del conto usano l'API della testnet di Hyperliquid

  Scenario: Un conto su Hyperliquid opera sulla rete reale in ogni suo uso
    Dato un'installazione senza alcuna impostazione della rete di Hyperliquid
    Quando un conto dichiara l'exchange "Hyperliquid"
    Allora lettura del conto, mercati, ordini, attività ed esecuzioni del conto usano l'API reale di Hyperliquid
