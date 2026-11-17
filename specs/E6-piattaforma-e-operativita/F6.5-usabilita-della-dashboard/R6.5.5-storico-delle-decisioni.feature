# language: it
@R6.5.5
Funzionalità: R6.5.5 Storico delle decisioni
  Come utente
  Voglio scorrere le decisioni dell'agente nel tempo, per asset
  Perché capisco come ragiona il flusso e se le sue scelte sono coerenti

  La pagina del flusso ha l'elenco delle decisioni: una riga per ciclo e asset con istante, asset, azione,
  direzione, confidenza e ragionamento accorciato, e il collegamento al ciclo. L'elenco usa la tabella condivisa
  (ordinamento, filtri, paginazione, R6.4.4), segue il periodo comune della pagina (R6.4.3) e si filtra per asset,
  azione e direzione. Azioni e direzioni hanno le icone di R6.5.3 (dipendenza: R6.5.3 prima). Il dato è disponibile
  anche dall'interfaccia programmatica.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con cicli conclusi negli ultimi 7 giorni su BTC ed ETH

  Scenario: Elenco delle decisioni
    Quando "anna" apre lo storico delle decisioni del flusso "alfa"
    Allora vede una riga per ciclo e asset con istante, asset, azione, direzione, confidenza e ragionamento accorciato
    E le più recenti in alto

  Scenario: Filtro per asset e azione
    Quando "anna" filtra lo storico per asset "BTC" e azione "apri"
    Allora vede solo le decisioni di aprire su BTC

  Scenario: Periodo comune
    Quando "anna" sceglie il periodo "7 giorni"
    Allora lo storico mostra solo le decisioni degli ultimi 7 giorni

  Scenario: Dal dettaglio al ciclo
    Quando "anna" sceglie una riga dello storico
    Allora apre il dettaglio del ciclo di quella decisione
