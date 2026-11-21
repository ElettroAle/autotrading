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

  Scenario: Scadenza indicata a mano
    Quando "anna" indica per la chiave "openrouter" la scadenza 15 dicembre 2026
    Allora la chiave mostra la scadenza 15 dicembre 2026

  Scenario: Rinnovo
    Dato che la chiave "openrouter" scade tra 5 giorni e "anna" ha ricevuto l'avviso a 7 giorni
    Quando "anna" sostituisce la chiave con una che scade il 15 marzo 2027
    Allora l'avviso nelle pagine Chiavi e Conti sparisce
    E "anna" riceverà di nuovo gli avvisi a 30, 7 e 1 giorno dalla nuova scadenza

  Scenario: Una nuova data azzera le soglie
    Dato che la chiave "openrouter" scade tra 5 giorni e "anna" ha ricevuto l'avviso a 7 giorni
    Quando "anna" indica per la chiave "openrouter" la scadenza 15 marzo 2027
    Allora "anna" riceverà di nuovo gli avvisi a 30, 7 e 1 giorno dalla nuova scadenza

  Scenario: Scadenza sconosciuta
    Dato che la chiave di un adapter di fonte non ha una data di scadenza
    Quando "anna" apre la pagina Chiavi
    Allora la chiave mostra "scadenza sconosciuta" e non genera avvisi
