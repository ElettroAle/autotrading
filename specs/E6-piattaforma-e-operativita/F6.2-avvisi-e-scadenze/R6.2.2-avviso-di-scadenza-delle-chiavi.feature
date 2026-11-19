# language: it
@R6.2.2
Funzionalità: R6.2.2 Avviso di scadenza delle chiavi
  Come utente
  Voglio essere avvisato prima che una chiave scada
  Perché la rinnovo in tempo e i miei flussi non si fermano

  Vale per tutte le chiavi: credenziali dei conti degli exchange, chiavi dei fornitori IA, credenziali degli
  adapter delle fonti (R4.1.2) e ogni chiave futura. La data di scadenza la legge l'adapter dal fornitore quando
  può (Hyperliquid espone la validità dell'API wallet) e la aggiorna a ogni verifica; altrimenti l'utente la indica
  alla registrazione o dopo. Senza data la chiave mostra "scadenza sconosciuta" e non genera avvisi. Gli avvisi
  partono 30, 7 e 1 giorno prima della scadenza e alla scadenza, una sola volta per soglia, su Telegram e nel
  campanello (R6.2.1), con nome della chiave, data di scadenza e flussi che la usano. Nelle pagine Chiavi e Conti
  una chiave in scadenza entro 30 giorni o scaduta ha un avviso visibile finché non è rinnovata. Alla scadenza i
  flussi che la usano vanno in pausa come per una chiave revocata (R1.2.4). Rinnovare la chiave, o indicare una
  nuova data, azzera le soglie.
  La chiave in scadenza entro 30 giorni è anche un avviso aperto «attenzione» nel centro degli avvisi (R6.2.3),
  «critica» alla scadenza; l'avviso si risolve da solo al rinnovo o quando la data si sposta.

  Contesto:
    Dato che "anna" ha la chiave del fornitore IA "openrouter" usata dai flussi "alfa" e "beta"

  Scenario: Scadenza letta dall'adapter
    Dato che "anna" ha un conto "Hyperliquid" il cui API wallet è valido fino al 30 dicembre 2026
    Quando la piattaforma verifica le credenziali del conto
    Allora il conto mostra la scadenza 30 dicembre 2026

  Scenario: Scadenza indicata a mano
    Quando "anna" indica per la chiave "openrouter" la scadenza 15 dicembre 2026
    Allora la chiave mostra la scadenza 15 dicembre 2026

  Schema dello scenario: Avvisi alle soglie
    Dato che la chiave "openrouter" scade il 15 dicembre 2026
    Quando è il <giorno>
    Allora "anna" riceve su Telegram e nel campanello l'avviso "<avviso>" con i flussi "alfa" e "beta"

    Esempi:
      | giorno            | avviso                                 |
      | 15 novembre 2026  | la chiave openrouter scade tra 30 giorni |
      | 8 dicembre 2026   | la chiave openrouter scade tra 7 giorni  |
      | 14 dicembre 2026  | la chiave openrouter scade domani        |
      | 15 dicembre 2026  | la chiave openrouter è scaduta           |

  Scenario: Un solo avviso per soglia
    Dato che "anna" ha già ricevuto l'avviso a 7 giorni per la chiave "openrouter"
    Quando la piattaforma ricontrolla le scadenze lo stesso giorno
    Allora "anna" non riceve un secondo avviso a 7 giorni

  Scenario: Pausa alla scadenza
    Dato che la chiave "openrouter" è scaduta
    Quando arriva il ciclo del flusso "alfa"
    Allora il flusso "alfa" è in pausa con il motivo "chiave openrouter scaduta"

  Scenario: Rinnovo
    Dato che la chiave "openrouter" scade tra 5 giorni e "anna" ha ricevuto l'avviso a 7 giorni
    Quando "anna" sostituisce la chiave con una che scade il 15 marzo 2027
    Allora l'avviso nelle pagine Chiavi e Conti sparisce
    E "anna" riceverà di nuovo gli avvisi a 30, 7 e 1 giorno dalla nuova scadenza

  Scenario: Scadenza sconosciuta
    Dato che la chiave di un adapter di fonte non ha una data di scadenza
    Quando "anna" apre la pagina Chiavi
    Allora la chiave mostra "scadenza sconosciuta" e non genera avvisi

  Scenario: Avviso aperto nel centro degli avvisi
    Dato che la chiave "openrouter" scade tra 20 giorni
    Quando la piattaforma controlla le scadenze
    Allora il centro degli avvisi ha un avviso aperto "attenzione" per la chiave "openrouter"
    E quando la chiave è scaduta l'avviso diventa "critica"
    E quando "anna" sostituisce la chiave con una che scade tra 90 giorni l'avviso è risolto
