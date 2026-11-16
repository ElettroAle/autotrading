# ADR chiusura-di-emergenza-nella-dashboard — Chiusura di emergenza nella dashboard con conferma dell'ambito

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.2.3 (460), Task T3.2.3.2 (483)
- Collegate: ADR 0116 (dashboard secondo bulletproof-react), ADR chiusura-di-emergenza-per-ambito, ADR
  pagina-del-flusso-a-schede-sotto-un-periodo-comune
- Dipende da: R3.1.2, come il Task T3.2.3.1

## Contesto e problema

La chiusura di emergenza si lancia dalla pagina del flusso, dalla pagina del conto e dall'elenco dei flussi (tutti
i flussi). Prima di chiudere, la dashboard chiede una conferma che nomina l'ambito e il numero di posizioni, poi
mostra l'esito per flusso.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove
  possibile, nessun duplicato per pagina.
- bulletproof-react: nessun import tra funzionalità; le pagine di `src/app` compongono le funzionalità.
- ADR 0116: il numero di posizioni arriva dall'API (anteprima), non da un calcolo della dashboard.

## Opzioni considerate

1. **Una funzionalità `features/emergency-closing` con un solo comando parametrizzato dall'ambito.** Il componente
   `EmergencyClosingCommand` riceve l'ambito (flusso con nome, conto con nome, tutti), legge l'anteprima e apre il
   `ConfirmationDialog` condiviso con il testo "Chiudere <N> posizioni del flusso <nome> e metterlo in pausa?",
   "Chiudere <N> posizioni dei flussi del conto <nome> e metterli in pausa?" o "Chiudere <N> posizioni di tutti i
   flussi e metterli in pausa?"; solo alla conferma chiama `POST /flows/emergency-closings`, mostra l'esito per
   flusso (posizioni chiuse, non chiuse col motivo, "nessuna posizione da chiudere") con i componenti condivisi e
   invalida flussi, posizioni e conti. Le pagine del flusso, del conto e dell'elenco lo compongono da `src/app`.
2. Un comando diverso in ogni funzionalità (flussi, conti): scartata, tre copie dello stesso comando.

## Esito della decisione

Opzione 1, con client OpenAPI rigenerato e mock di `src/testing/mocks` aggiornati.

Verifica: prova (scenario "Conferma nella dashboard" di R3.2.3 con playwright-bdd, unit test del comando, del testo
di conferma e dell'esito).

### Conseguenze

- Un solo componente per i tre ambiti; il comando è distruttivo e si presenta come tale.
