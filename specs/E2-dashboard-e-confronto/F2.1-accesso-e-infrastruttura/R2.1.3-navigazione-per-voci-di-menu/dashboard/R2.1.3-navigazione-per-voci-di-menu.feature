# language: it
@R2.1.3
Funzionalità: R2.1.3 Navigazione per voci di menu
  Come utente
  Voglio raggiungere ogni area della dashboard dal menu, raggruppata per uso
  Perché trovi subito ciò che cerco senza scorrere la pagina dei flussi

  Il menu ha le voci Flussi, Conti, Storico e, nel gruppo Impostazioni, Chiavi e Notifiche. La voce dell'area in
  cui si trova l'utente è evidenziata, anche nelle sue sotto-pagine. Le azioni sui flussi (nuovo flusso,
  importazione, classifica) stanno nella pagina dei flussi. Sul telefono il menu resta nel pannello ripiegato
  (R2.1.2).

  Fuori ambito: il cambio degli indirizzi delle pagine e la personalizzazione del menu da parte dell'utente.

  Scenario: Voci del menu raggruppate
    Quando "anna" apre la dashboard
    Allora il menu ha le voci "Flussi", "Conti", "Storico"
    E ha il gruppo "Impostazioni" con le voci "Chiavi" e "Notifiche"

  Scenario: Voce attiva anche nelle sotto-pagine
    Quando "anna" apre il dettaglio del flusso "alfa"
    Allora la voce "Flussi" del menu è evidenziata

  Scenario: Azioni dei flussi nella pagina dei flussi
    Quando "anna" apre la pagina dei flussi
    Allora la pagina offre "Nuovo flusso", "Importa" e la vista "Classifica"
    E la pagina non ha collegamenti a conti, storico, chiavi o notifiche

  Scenario: Importazione su richiesta
    Quando "anna" sceglie "Importa" nella pagina dei flussi
    Allora compare il modulo di importazione di una strategia

  Scenario: Titoli generici delle impostazioni
    Quando "anna" apre la voce "Chiavi"
    Allora la pagina si intitola "Chiavi" e contiene la sezione delle chiavi dei fornitori IA
