# ADR 0038 — Risposta, contesto e costo dell'agente come regole del domain

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.4.3, R1.4.4, R1.4.5, R1.4.6 (Task T1.4.3.1, T1.4.4.1, T1.4.5.1, T1.4.6.1)

## Contesto

A ogni ciclo l'agente riceve un contesto (R1.4.3) e risponde con una decisione per asset (R1.4.4); una
decisione non conforme si scarta con il motivo, una risposta non leggibile scarta tutto (R1.4.5); ogni chiamata
registra token e costo (R1.4.6). I motivi di scarto del requisito nominano i campi in italiano ("campo
obbligatorio mancante: direzione", "valore fuori dall'intervallo: quota"). Il ciclo (F1.2) e la chiamata al
modello non esistono ancora: gli scenari restano `@wip` finché non arrivano.

## Decisione

- **Formato della risposta**: un oggetto JSON `{"decisioni": [...]}`, una voce per asset con `asset`, `azione`
  (`apri`, `chiudi`, `mantieni`), `direzione` (`long`, `short`), `quota` (frazione del capitale da 0 a 1,
  estremi inclusi), `leva` (intero da 1) e `ragionamento`. Le chiavi sono quelle dei motivi di scarto: il
  motivo nomina il campo come il modello l'ha ricevuto.
- **Lettura** in `AgentResponse.read(testo, asset del flusso)` nel domain di `agent`:
  - controlli nell'ordine asset, azione, ragionamento, poi per `apri` direzione, quota e leva; il primo che
    fallisce dà il motivo;
  - i campi operativi di `chiudi` e `mantieni` si ignorano; la chiusura è sempre totale;
  - l'asset si legge in maiuscolo; due decisioni sullo stesso asset sono ambigue e si scartano entrambe
    ("decisione ripetuta per l'asset: BTC");
  - un asset senza decisione è mancante (trattato come mantieni); un asset con decisione scartata non lo è;
  - una risposta che non è JSON, o non ha l'elenco `decisioni`, è non leggibile: ogni asset del flusso ha una
    decisione scartata con "risposta non leggibile" e il testo integrale resta registrato;
  - un blocco di codice Markdown attorno al JSON si toglie: è un'abitudine dei modelli, non un altro formato;
  - i numeri si leggono come `Decimal`; un booleano non vale come numero.
  - La leva oltre il massimo del flusso non è un caso di non conformità: è il controllo del rischio (R1.5.2).
- **Contesto** in `AgentContext.messages()`: un messaggio di sistema con istruzioni, regole operative (una
  posizione per asset, azioni ammesse, leva da 1 al massimo del flusso, una decisione per asset, chiusura
  totale) e formato della risposta; un messaggio utente con un documento JSON: ora corrente, tempo dall'avvio
  detto a parole ("2 ore e 30 minuti"), stato del solo flusso (capitale allocato, liquidità disponibile,
  valore complessivo, rendimento, posizioni), fonti con pesi e dati mancanti. Il contesto non ha campi per il
  saldo del conto o per altri flussi: non li può contenere.
- **Costo** in `ModelUsage.cost_usd(prezzi)`: il costo riportato dal fornitore, altrimenti token per prezzo del
  catalogo per milione, altrimenti non disponibile. Il catalogo dei modelli accetta `prices` facoltativi
  (`input_per_million`, `output_per_million`).

## Alternative scartate

- **Chiavi della risposta in inglese**: i motivi di scarto del requisito sono in italiano e nominano il campo;
  tradurre tra le due forme è un passo in più senza valore.
- **Scarto dell'intera risposta per una sola decisione errata**: il requisito vuole che le decisioni conformi
  proseguano.
- **Prima decisione valida tra due sullo stesso asset**: sceglierne una è un'interpretazione; nessuna delle due
  diventa un ordine.
- **Prezzi dei modelli scritti ora nel catalogo**: cambiano spesso e OpenRouter riporta il costo da sé; senza
  prezzi il costo è "non disponibile", come il requisito prevede.

## Conseguenze

- La chiamata al modello (porta, adapter per fornitore, errori permanenti di chiave e credito) e il
  collegamento al ciclo arrivano con F1.2.
- Il costo totale per flusso e per giorno UTC arriva con la registrazione dei cicli (R1.7.1).
