# ADR 0126 — L'elenco dei conti porta rete e capitale allocato; la dashboard compone il saldo a parte

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.1 (Task T2.2.1.1)
- Collegate: ADR 0116, ADR 0119; R0.2.1 (rete dall'installazione, `ExchangeNetwork.of_installation`), R0.2.2
  (`GET /accounts/{id}/state`), R1.1.7 (`GET /accounts/{id}/free-capital`); CLAUDE.md «Niente ponti tra contesti»;
  `.claude/rules/tech-dashboard.md` (nessuna logica di business che l'API non esponga); ADR 0018

## Contesto e problema

La pagina dei conti mostra nome, rete (testnet o mainnet), saldo letto dall'exchange, capitale allocato ai flussi e
capitale libero. L'API oggi non espone né la rete del conto né il capitale allocato per conto: questo si calcola
solo dentro il capitale libero, che legge il saldo dall'exchange e quindi fallisce quando l'exchange non risponde,
proprio quando lo scenario chiede di mostrare comunque il capitale allocato.

## Decisione

- `GET /accounts` (e `GET /accounts/{id}`) aggiunge `network`, dalla regola del dominio che ricava la rete
  dall'installazione (R0.2.1), e `allocated_capital` (stringa), la somma del capitale allocato dei flussi del conto
  non archiviati e non in bozza.
- Il contesto `accounts` dichiara nel proprio `ports.py` la porta che legge il capitale allocato di un conto, con i
  suoi errori; la realizza l'adapter `sqlalchemy` nella sua cartella, che ha i flussi. Nessun ponte verso il
  contesto `flows`; la sequenza sta nel caso d'uso dell'elenco dei conti.
- Frontend `accounts`: elenco da `GET /accounts`, poi per ogni conto due query TanStack indipendenti (stato e
  capitale libero), così un exchange che non risponde rende «saldo non disponibile» solo quelle celle, mentre rete e
  capitale allocato restano visibili. Nessun valore ricalcolato nel browser.

## Alternative scartate

- **Capitale allocato sommato nel browser da `GET /flows` e rete ricavata da `environment`**: nessun cambio di API,
  ma copia nel browser due regole del dominio (tech-dashboard.md).
- **Endpoint aggregato nuovo per la pagina**: una sola chiamata, ma fallirebbe tutto insieme quando l'exchange non
  risponde.

## Conseguenze

- La pagina fa 1 + 2N chiamate per N conti, accettabile per un utente con pochi conti.
- La regola «capitale allocato del conto» ha ora due letture (dentro il capitale libero e nell'elenco): il caso d'uso
  del capitale libero riusa la stessa porta se lo sviluppo lo rende possibile senza cambiare il suo contratto.
