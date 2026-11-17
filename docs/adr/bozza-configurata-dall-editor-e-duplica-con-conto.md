# ADR bozza-configurata-dall-editor-e-duplica-con-conto — Conto, capitale e asset della bozza dall'editor; Duplica copia conto e capitale

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 555, Task 556; R2.4.1, R1.1.2 (RF-02.05)
- Collegate: ADR 0124 (sostituita in parte: la copia porta conto e capitale; l'assegnazione passa dall'editor), ADR
  nome-del-flusso-modificabile
- Verifica: prova

## Contesto e problema

Una bozza riceve conto, capitale e asset solo da `PUT /flows/{flow_id}/assignment` (`AssignDraftFlowUseCase`), un form
nella panoramica del flusso. L'editor (`PATCH /flows/{flow_id}`, `ModifyFlowUseCase`) rifiuta qualunque conto con
`AccountNotChangeableError` («il conto di un flusso non si cambia»), perché su una bozza `flow.account_id` è vuoto, e
non accetta il capitale. Duplica (`Flow.duplicated`) crea una bozza senza conto né capitale. Il proprietario
(17/11/2026) vuole conto, capitale e asset della bozza nella configurazione, e la copia con conto e capitale
dell'origine ma senza asset.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): «Conto e capitale, asset no»; il form di assegnazione nella panoramica è
  fuori contesto.
- RF-02.05: due flussi sullo stesso conto non hanno asset in comune; il controllo resta all'avvio
  (`require_assets_free`), dove oggi già sta.
- CLAUDE.md: un caso d'uso per operazione, nessuna copia provvisoria che resti accanto a quella canonica.
- Dopo l'avvio il conto non si cambia (R1.1.1) e il capitale cambia solo con `PUT /flows/{id}/allocated-capital`.

## Decisione

- Domain: una bozza può avere un'assegnazione parziale (conto e capitale senza asset, o nessuno dei tre);
  l'invariante di `Flow.__post_init__` continua a esigere conto, capitale e almeno un asset fuori dalla bozza.
  `Flow.duplicated` copia dall'origine `account_id` e capitale allocato, con asset vuoti.
- Application: `ModifyFlowCommand` riceve `allocated_capital: Decimal | None`. Su una bozza `ModifyFlowUseCase`
  accetta conto, capitale e asset (anche uno solo), con i controlli oggi in `AssignDraftFlowUseCase`: conto
  esistente del tenant, asset negoziabili sull'exchange del conto, capitale non oltre quello libero; il risultato è
  una nuova versione della configurazione. Fuori dalla bozza un conto diverso resta `AccountNotChangeableError` e un
  capitale diverso è rifiutato con un errore tipizzato che rimanda al comando del capitale.
- Spariscono `AssignDraftFlowUseCase`, `PUT /flows/{flow_id}/assignment` e i loro test: l'editor è l'unico ingresso.
- Duplica non verifica il capitale libero: la bozza non impegna capitale, il controllo resta all'avvio e al
  salvataggio dell'editor.
- Scenari: quelli di R2.4.1 sulla duplicazione e sull'assegnazione si riallineano (la copia ha conto e capitale
  dell'origine; l'assegnazione avviene dalla configurazione).

## Alternative scartate

- Tenere `PUT /assignment` accanto all'editor: due ingressi per lo stesso dato.
- Copiare anche gli asset: l'avvio fallirebbe sempre per RF-02.05 sullo stesso conto (scartata dal proprietario).

## Conseguenze

- La copia di un flusso si avvia scegliendo solo gli asset.
- L'importazione di una strategia (R2.5.2) crea ancora una bozza senza conto, configurata poi dall'editor.
