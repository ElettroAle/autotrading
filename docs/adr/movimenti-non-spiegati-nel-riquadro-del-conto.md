# ADR movimenti-non-spiegati-nel-riquadro-del-conto — Il registro dei non attribuibili nel riquadro del conto

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 596, Task 600; R1.6.2, R3.3.2
- Collegate: ADR conti-a-riquadri, ADR stato-della-riconciliazione-nella-dashboard, ADR 0074 (pagine per keyset),
  ADR delle tabelle filtrabili (R6.4.4), `.claude/rules/tech-dashboard.md` §Pagine di impostazioni
- Verifica: prova

## Contesto e problema

I non attribuibili si registrano (`unattributable_items`) ma nessuna API né pagina li mostra: il link della notifica
porta agli allarmi, vuoti. Il proprietario (17/11/2026) vuole riconciliazione e registro nel conto, in Conti, come il
registro attività di una risorsa nei portali (Azure, GitHub).

## Fattori decisionali

- Decisione del proprietario (17/11/2026): impostazioni e registro sul conto; gli avvisi in una pagina unica (R6.2.3).
- Componenti condivisi della dashboard: `DataTable`, filtri condivisi, formattazione degli importi.
- Pagine per keyset dalla più recente, come lo storico (ADR 0074).

## Decisione

- Porta: `ReconciliationRepositoryPort.unattributable_of(account_id, filter, cursor) -> UnattributablePage` con le
  righe (istante, genere, asset, importo o quantità), il cursore della pagina successiva e il totale netto delle
  variazioni del saldo nel filtro, in una sola query aggregata; filtro per genere e periodo. Caso d'uso
  `ListUnattributableUseCase` in `application/flows`.
- API: `GET /accounts/{account_id}/reconciliation/unattributable?kind=&since=&until=&cursor=`, pagine di 50 dalla più
  recente, legate al tenant; client generato aggiornato.
- Dashboard: nel riquadro del conto, sotto la sezione Riconciliazione, la sezione «Movimenti non spiegati» con
  `DataTable` (Rilevato il, Tipo, Asset, Importo), filtri condivisi per tipo e periodo (ultime 24 ore predefinito),
  il totale netto delle variazioni del periodo sopra la tabella e il comando «Altri» per la pagina successiva; testo
  vuoto «Nessun movimento non spiegato nel periodo». Su telefono la tabella condivisa si legge senza scorrere di lato.
- Prove: integrazione del repository (pagine, filtri, totale, RLS); unit test di caso d'uso, API e componenti.

## Alternative scartate

- Pagina a sé per i movimenti: il registro appartiene al conto (decisione del proprietario).
- Movimenti dentro la pagina Allarmi: gli allarmi diventano avvisi di R6.2.3.

## Conseguenze

- Ogni variazione si ritrova nel conto con il totale del periodo.
