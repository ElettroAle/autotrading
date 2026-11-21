# language: it
@R2.2.1
Funzionalità: R2.2.1 Riepilogo dei conti
  Come utente
  Voglio vedere per ogni conto saldo, capitale allocato e capitale libero
  Perché sappia quanto capitale posso ancora assegnare

  Per ogni conto la dashboard mostra nome, ambiente, saldo letto dall'exchange, capitale allocato ai flussi e
  capitale libero (RF-23.02), con i valori dell'interfaccia programmatica (R0.2.2, R1.1.7).

  Fuori ambito: lo stato della riconciliazione e gli allarmi (F3).

  Contesto:
    Dato che "anna" ha il conto "principale" su testnet con saldo 1000 USDC
    E che i flussi "alfa" e "beta" hanno allocato 300 e 200 USDC sul conto "principale"

  Scenario: Riepilogo di un conto
    Quando "anna" apre la pagina dei conti
    Allora il conto "principale" mostra ambiente "testnet", saldo 1000 USDC, capitale allocato 500 USDC e capitale libero 500 USDC

  Scenario: Nessun conto
    Dato che "bruno" non ha conti
    Quando "bruno" apre la pagina dei conti
    Allora la pagina mostra "Nessun conto registrato" e il comando per registrarne uno

  Scenario: Exchange non raggiungibile
    Dato che l'exchange non risponde
    Quando "anna" apre la pagina dei conti
    Allora il conto "principale" mostra "Saldo non disponibile" al posto del saldo
    E mostra il capitale allocato 500 USDC
