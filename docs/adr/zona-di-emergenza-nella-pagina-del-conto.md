# ADR zona-di-emergenza-nella-pagina-del-conto — La chiusura di emergenza di un conto sta nella pagina del conto

- Stato: proposta (22 novembre 2026)
- Requisiti: Bug 632 (Task 705)
- Collegate: ADR zona-di-emergenza-in-fondo-alla-pagina, ADR elenco-dei-conti-e-pagina-del-conto, ADR
  chiusura-di-emergenza-nella-dashboard, ADR 0116 (bulletproof-react); Bug 545, Bug 563
- Verifica: prova

## Contesto e problema

La pagina dell'elenco dei conti mostra in fondo la «Zona di emergenza» con «Chiusura di emergenza del conto …»: un
comando irreversibile sulla pagina di elenco invece che su quella dell'oggetto. Per i flussi lo stesso problema è già
stato corretto (Bug 545, Bug 563): la zona di emergenza sta nella pagina del flusso.

## Fattori decisionali

- Decisione del proprietario (17/11/2026, ADR zona-di-emergenza-in-fondo-alla-pagina): riquadro «Zona di emergenza»
  a sé, bordo rosso, in fondo alla pagina, con la conferma di oggi; un solo componente condiviso.
- ADR elenco-dei-conti-e-pagina-del-conto: ogni conto ha la sua pagina.
- Richiesta del proprietario (22/11/2026): sviluppare tutto in autonomia; la proposta del Bug si adotta.

## Decisione

- La pagina del conto mostra in fondo la «Zona di emergenza» con la chiusura di emergenza di quel conto, con lo stesso
  componente condiviso e la stessa `ConfirmationDialog` di oggi.
- L'elenco dei conti non mostra comandi di emergenza.
- Nessun cambio all'API né al comando.

## Alternative scartate

- Lasciare la zona nell'elenco: contraddice la regola già applicata ai flussi.

## Conseguenze

- Per chiudere in emergenza un conto si apre la sua pagina: un passo in più, voluto.
