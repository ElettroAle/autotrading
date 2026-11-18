# ADR pagina-avvisi-nella-dashboard — Pagina Avvisi, dettaglio e numero degli aperti nel menu

- Stato: proposta (18 novembre 2026)
- Requisiti: R6.2.3, Task 609; R3.3.2
- Collegate: ADR api-degli-avvisi-e-link-nelle-notifiche, ADR 0119 (layout), ADR 0160 (menu a gruppi), ADR delle
  tabelle filtrabili (R6.4.4), ADR icone-con-lucide-react-e-comandi-condivisi, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

Serve la pagina unica degli avvisi, come Azure Monitor > Alerts o GitHub Security alerts (decisione del proprietario,
17/11/2026), e la pagina Allarmi del conto confluisce in essa.

## Fattori decisionali

- Componenti condivisi: `DataTable`, filtri condivisi, `CommandButton`, icone da `components/ui/icons`.
- Gravità con icona e testo, mai solo colore; su telefono la tabella condivisa si legge senza scorrere di lato.
- Nessuna logica di business nella dashboard: comandi ammessi e risoluzione li dà l'API.

## Decisione

- Funzionalità `features/alerts`: rotte `/alerts` e `/alerts/:alertId`.
- Elenco: `DataTable` con Gravità (icona e testo: «Critica» rossa, «Attenzione» ambra), Avviso, Risorsa interessata
  (collegamento a conto o flusso), Aperto il, Stato; filtri condivisi per stato (predefinito «Aperti»), gravità, tipo
  di risorsa e periodo, tenuti nell'indirizzo; testo vuoto «Nessun avviso aperto».
- Dettaglio: titolo e gravità, «Che cosa è successo» con i valori, «Che cosa fare» con i comandi ammessi dall'API
  (Conferma il saldo, Riprendi il flusso, Segna come risolto) con il dialogo di conferma condiviso, collegamento alla
  risorsa; un avviso risolto mostra quando.
- Menu: voce «Avvisi» nel primo gruppo con il numero degli aperti (`GET /alerts/summary`) letto con la rilettura della
  pagina (R2.1.2); nessun numero con zero aperti.
- `/accounts/:accountId/alarms` reindirizza agli avvisi filtrati per il conto con tutti gli stati; il comando
  «Allarmi» del riquadro del conto porta lì.
- Prove: unit test dei componenti con i finti MSW; scenari Playwright di R6.2.3 (`specs/E6-*/F6.2-*` aggiunto alle
  `features` di `playwright.config.ts`).

## Alternative scartate

- Pannello a comparsa al posto della pagina: il pannello è il campanello delle notifiche (R6.2.1); gli avvisi hanno
  filtri e dettaglio.

## Conseguenze

- Ogni intervento richiesto si trova in un punto, con la strada per risolverlo.
