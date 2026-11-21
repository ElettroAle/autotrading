# language: it
@R2.3.8
Funzionalità: R2.3.8 Exchange e fornitori IA scelti da un elenco
  Come utente
  Voglio scegliere l'exchange di un conto e il fornitore di una chiave IA da un elenco
  Perché non debba conoscerne il nome esatto e non registri un valore che la piattaforma rifiuta

  L'elenco degli exchange è quello che la piattaforma supporta; l'elenco dei fornitori è quello del catalogo dei
  modelli (R1.4.2). Gli elenchi vengono dall'API e usano lo stesso campo condiviso della scelta degli asset.
  Un fornitore di cui l'utente ha già la chiave compare come già registrato e non si sceglie: la chiave si
  sostituisce (R2.3.2).

  Scenario: Exchange del conto da un elenco
    Dato che la piattaforma supporta l'exchange "Hyperliquid"
    Quando "anna" apre la registrazione di un conto
    Allora il campo exchange offre "Hyperliquid" e non accetta un valore fuori dall'elenco

  Scenario: Fornitore della chiave da un elenco
    Dato che il catalogo dei modelli ha i fornitori "openrouter" e "anthropic"
    Quando "anna" apre la registrazione di una chiave IA
    Allora il campo fornitore offre "openrouter" e "anthropic"

  Scenario: Fornitore con chiave già registrata
    Dato che "anna" ha registrato la chiave del fornitore "openrouter"
    Quando "anna" apre la registrazione di una chiave IA
    Allora il fornitore "openrouter" risulta già registrato e non si può scegliere

  Scenario: Elenco non disponibile
    Dato che l'API non riesce a fornire l'elenco degli exchange
    Quando "anna" apre la registrazione di un conto
    Allora il modulo segnala che l'elenco non è disponibile e non permette la registrazione
