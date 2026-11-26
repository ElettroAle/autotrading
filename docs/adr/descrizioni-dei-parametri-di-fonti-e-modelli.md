# ADR descrizioni-dei-parametri-di-fonti-e-modelli — Descrizioni dei parametri dichiarate dagli adapter delle fonti e dai modelli

- Stato: accettata (26 novembre 2026)
- Requisiti: US 772 R5.5.7 (Task 774)
- Collegate: ADR parametri-delle-fonti-come-liste-libere, ADR fonti-con-adapter-dichiarati, ADR
  informazioni-sui-campi-di-configurazione; `.claude/rules/context-sources.md`, `.claude/rules/context-agent.md`,
  `.claude/rules/tech-fastapi.md`
- Verifica: prova

## Contesto e problema

R5.5.7 chiede che il testo info di un parametro di un adapter di fonte e di un parametro di modello sia la descrizione
che quell'adapter o quel modello dichiara, non vuota per ogni parametro, esposta dagli elenchi dell'API.

## Fattori decisionali

- I parametri di una fonte li dichiara il suo adapter (ADR parametri-delle-fonti-come-liste-libere).
- I parametri di un modello vengono dal catalogo dei modelli; nessun codice per un fornitore nel domain.
- Ambiguità risolta: «la descrizione che quel modello dichiara» — il catalogo dei fornitori non dà descrizioni in
  italiano dei parametri. Si legge come la descrizione che la piattaforma dichiara per ogni parametro di modello che
  offre, in un solo punto del contesto `agent`, uguale per ogni modello che lo ammette.

## Decisione

- La dichiarazione di un parametro di adapter ha un campo `description` obbligatorio e non vuoto (invariante del
  domain); ogni adapter dichiara le descrizioni dei suoi parametri, in italiano, nell'ordine: che cosa fa, valori
  ammessi, predefinito.
- Ogni parametro di modello che la piattaforma offre ha una descrizione in italiano in un solo elenco del contesto
  `agent`; un parametro offerto senza descrizione è un errore che la prova rileva.
- Gli elenchi dell'API delle fonti e dei modelli espongono la descrizione; la dashboard la mostra con il pulsante info.
- Prove: una prova percorre ogni adapter dichiarato e ogni parametro di modello offerto e fallisce per una descrizione
  mancante o vuota.

## Alternative scartate

- **Descrizioni nella dashboard**: la dashboard non ha conoscenza propria dei parametri (ADR 0116).

## Conseguenze

- Un adapter o un parametro nuovo senza descrizione non passa le prove.
