# ADR 0084 — Collegamento obbligatorio delle pull request ai work item

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.5.1 (Task T0.5.5)
- Collegate: ADR 0001-0013 (pipeline TrunkFlow e controlli obbligatori su `main`)

## Contesto

La board Azure DevOps è la fonte di verità del lavoro, e `docs/architecture.md` dichiara che il repository si
collega alla board con `AB#<id>`. La connessione Azure Boards ↔ GitHub del progetto crea il collegamento sul work
item quando titolo o descrizione della pull request contengono `AB#<id>`, ed è letta anche a posteriori. Il riferimento
però era affidato a chi scriveva la pull request: molte pull request citavano il requisito solo come testo
(«Bug 172», «R1.8.1»), che la board non riconosce, e i loro work item restavano senza collegamento.

## Decisione

- Un controllo della pipeline di qualità, job `work item` di `reusable-quality.yml` (contesto `quality / work item`),
  fallisce se la descrizione della pull request non contiene almeno un `AB#<numero>`. Il messaggio dice che cosa
  aggiungere: il requisito o il Bug e ogni Task che la pull request realizza.
- Il controllo è nei controlli obbligatori del ruleset `main protetto`: una pull request senza collegamento non si
  integra, nemmeno con l'auto-merge.
- Il workflow `quality` si attiva anche su `edited`: correggere la descrizione rilancia il controllo senza un nuovo
  commit.
- La regola vive in `tools/work_item_link.py` (stessi principi di `tools/`); la descrizione arriva sullo stdin, mai
  come argomento di un comando.
- Esenzione solo per l'autore `dependabot[bot]`, che apre le proprie pull request senza poter citare un work item.
- Il controllo verifica la forma del riferimento, non l'esistenza del work item: chiedere alla board richiederebbe una
  credenziale Azure DevOps nella pipeline, che il progetto esclude (niente PAT).

## Alternative scartate

- **Regola del ruleset sul messaggio di commit (`commit_message_pattern`)**: controlla i commit al momento del push su
  `main`, non la pull request. L'errore arriverebbe solo all'integrazione, senza un controllo visibile sulla pull
  request, e varrebbe per ogni commit invece che per la pull request.
- **Riferimento nel titolo**: il titolo è un Conventional Commit verificato da `quality / titolo` e diventa la riga
  del changelog; più work item lo renderebbero illeggibile.
- **Verifica dell'esistenza sulla board**: richiede una credenziale di Azure DevOps nella pipeline.

## Conseguenze

- Ogni pull request integrata compare sui suoi work item insieme al commit di squash, che riporta la descrizione.
- Modificare la descrizione rilancia tutti i controlli di qualità, non solo questo.
- Un riferimento a un id sbagliato passa il controllo; lo si vede sul work item, che non mostra la pull request.
