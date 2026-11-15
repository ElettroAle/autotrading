# language: it
@R2.3.11
Funzionalità: R2.3.11 Exchange di test selezionabile
  Come utente
  Voglio scegliere alla registrazione del conto se opera su Hyperliquid o su Hyperliquid Testnet
  Perché la rete del conto si capisca dall'exchange che scelgo, senza dipendere da come è configurata l'installazione

  Ogni installazione offre sempre entrambi gli exchange; nessuna impostazione dell'installazione sceglie la rete.
  L'exchange di test è un adapter dedicato che eredita da quello reale e ne cambia solo rete e indirizzo dell'API.
  L'avviso della rete di test e la conferma del denaro reale seguono l'exchange del conto (R2.3.10, R2.3.4).

  Contesto:
    Dato gli exchange "Hyperliquid" sulla rete reale "mainnet" e "Hyperliquid Testnet" sulla rete di test "testnet"

  Scenario: Si sceglie tra l'exchange reale e quello di test
    Quando "anna" chiede gli exchange supportati
    Allora gli exchange sono "Hyperliquid" sulla rete reale "mainnet" e "Hyperliquid Testnet" sulla rete di test "testnet"

  Schema dello scenario: Un conto opera sull'exchange che dichiara
    Quando "anna" registra il conto "<conto>" sull'exchange "<exchange>"
    Allora le credenziali del conto "<conto>" le controlla solo l'exchange "<exchange>"
    E l'elenco dei conti di "anna" mostra "<conto>" sulla rete <tipo> "<rete>"

    Esempi:
      | conto      | exchange            | tipo    | rete    |
      | prove      | Hyperliquid Testnet | di test | testnet |
      | principale | Hyperliquid         | reale   | mainnet |
