# ADR assegnazione-della-bozza-nel-form-di-configurazione — Conto, capitale e asset nel form di configurazione

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 555, Task 557
- Collegate: ADR bozza-configurata-dall-editor-e-duplica-con-conto, `.claude/rules/tech-dashboard.md` §Pagine di
  impostazioni, ADR 0119 (struttura bulletproof-react)
- Verifica: prova

## Contesto e problema

Nella dashboard il form dell'editor (`features/flow-editor/components/flow-form.tsx`) mostra un select «Conto» che il
salvataggio rifiuta, e non mostra il capitale; la panoramica di una bozza (`features/flows/components/flow-opening.tsx`)
mostra `DraftAssignmentForm` con conto, capitale e asset.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): assegnazione nella configurazione, non nella panoramica.
- Componenti condivisi: `SelectField`, `InputField`, `AssetPicker`, `FormAlert`; nessun import tra funzionalità.

## Decisione

- `flow-form.tsx`, per una bozza: «Conto» selezionabile e preselezionato col conto del flusso (quello copiato da
  Duplica), «Capitale allocato» modificabile, asset modificabili; tutto salvato con `PATCH /flows/{flow_id}`
  (`allocated_capital` nello schema rigenerato). Fuori dalla bozza il conto è in sola lettura e il capitale
  resta modificabile come oggi, salvato con `PUT /flows/{flow_id}/allocated-capital` (R1.1.7, R2.3.3).
- Panoramica di una bozza: al posto di `DraftAssignmentForm` un avviso con ciò che manca all'avvio e il collegamento
  «Configura» all'editor. Spariscono `draft-assignment-form.tsx`, `api/assign-draft-flow` e i loro test.
- Prove: unit test del form (bozza con conto preselezionato, salvataggio con conto/capitale/asset, sola lettura
  fuori dalla bozza) e della panoramica.

## Alternative scartate

- Lasciare il form nella panoramica accanto all'editor: due posti per lo stesso dato.

## Conseguenze

- La pagina Impostazioni del flusso (Bug 560) ospiterà questo stesso form.
