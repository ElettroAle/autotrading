# ADR esposizione-massima-per-direzione-del-conto — Esposizione massima per direzione sul conto

- Stato: accettata (26 novembre 2026)
- Requisiti: US 765 R5.5.5 (Task 766)
- Collegate: `.claude/rules/context-accounts.md`, `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-fastapi.md`,
  `.claude/rules/tech-mcp.md`
- Verifica: prova

## Contesto e problema

R5.5.5 chiede sul conto un'impostazione facoltativa, l'esposizione massima per direzione: una percentuale maggiore di 0
del saldo del conto letto dall'exchange. Si imposta e si toglie dal conto (API e dashboard) e si legge anche dagli
strumenti MCP; non si imposta dagli strumenti MCP (fuori ambito).

## Fattori decisionali

- Requisito R5.5.5 e il motivo di rifiuto letterale «l'esposizione massima per direzione è maggiore di 0».
- Ordine del proprietario per F5.5: impostazione facoltativa, vuota di default; i conti esistenti la leggono vuota.
- Il conto è del contesto `accounts`; il limite è una sua proprietà, non del singolo flusso.

## Decisione

- **Domain.** Il conto ha `max_direction_exposure_percent` facoltativa, con l'invariante nel domain (errore tipizzato
  con il motivo del criterio, maggiore di 0, valore finito).
- **Casi d'uso.** Un caso d'uso del contesto `accounts` imposta o toglie il limite del conto del tenant; la lettura dei
  conti lo restituisce.
- **Adapter.** Colonna facoltativa sulla tabella dei conti (migrazione, nessun valore per i conti esistenti), sotto RLS;
  API dei conti in lettura e modifica; strumenti MCP solo in lettura dei conti.

## Alternative scartate

- **Limite sul flusso**: il requisito parla dell'insieme dei flussi di un conto.

## Conseguenze

- Un conto senza limite si comporta come oggi.
