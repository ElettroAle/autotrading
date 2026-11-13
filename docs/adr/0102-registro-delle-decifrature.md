# ADR 0102 — Registro delle decifrature nel log dell'adapter libsodium

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.2.3, R1.4.1; Bug B1.0.2 (179)
- Collegate: ADR 0007 (credenziali cifrate nel database), ADR 0029 (chiavi dei fornitori IA), ADR 0021 (worker),
  docs/architecture.md §8.2 (modello di minaccia)

## Contesto e problema

Il modello di minaccia chiede che ogni decifratura registri conto e momento, mai il contenuto, e conta su quel
registro per rilevare un uso improprio. Né `SodiumCredentialOpenerAdapter` né `SodiumProviderKeyOpenerAdapter`
registravano qualcosa. In più nessun servizio configurava il logging: uvicorn configura solo i propri logger, quindi
i messaggi INFO dell'applicazione non arrivavano all'output del container.

## Decisione

- **Dove**: nel log dell'adapter libsodium, logger `autotrading.credentials`, a ogni apertura, riuscita o rifiutata.
  È il «registro applicativo» che ADR 0007 indica, e la decifratura è un fatto della tecnologia che la compie: il
  caso d'uso non sa né deve sapere che le credenziali sono sigillate.
- **Cosa**: scopo (conto, ordini, flussi, ciclo, verifica, modello), tenant, conto o fornitore della chiave, versione della
  chiave, esito. Un'apertura riuscita è INFO, una rifiutata WARNING. Mai il segreto, l'indirizzo o parti di essi.
- **Momento**: l'istante del record, in UTC ISO 8601, scritto dal formato del log.
- **Uscita**: la configurazione del logging di uvicorn (`deploy/logging.json`, copiata nell'immagine e passata con
  `--log-config` ai due servizi) manda i record dell'applicazione dal livello INFO all'output standard del container,
  con `UtcFormatter` dell'adapter FastAPI per il momento in UTC. I client HTTP (`httpx`, `httpcore`) restano a
  WARNING, perché i loro record contengono indirizzi con token (il bot Telegram lo mette nel percorso).

## Confronto con le decisioni scritte

- docs/architecture.md:230 «ogni decifratura registra conto e momento, mai il contenuto»: rispettata.
- docs/architecture.md:235 «Rilevazione: registro delle decifrature»: il registro è ora leggibile nel log del worker.
- ADR 0007, Conseguenze, «la decifratura si registra nel registro applicativo»: rispettata.
- .claude/rules/tech-libsodium.md «le credenziali in chiaro e le chiavi non compaiono in log»: verificato dai test.
- CLAUDE.md, un adapter una tecnologia: il log è della libreria standard, nessuna tecnologia nuova.
- Esito: nessuno scostamento.

## Alternative scartate

- **Tabella delle decifrature in PostgreSQL**: l'apertura avviene nell'adapter libsodium, che non può scrivere nel
  database (un adapter, una tecnologia); servirebbe un passo in ogni caso d'uso che apre credenziali, in cinque
  contesti. Contro root sulla macchina il database non è più affidabile del log.
- **Configurare il logging da codice nelle fabbriche dei servizi**: logica in `bootstrap.py`, che deve solo comporre,
  e stato globale del processo cambiato a ogni creazione dell'applicazione, anche nei test.
- **Formato JSON del log**: utile con un raccoglitore di log, che l'installazione non ha.

## Conseguenze

- Ogni ciclo con ordini produce alcune righe nel log del worker: dimensione trascurabile.
- I messaggi INFO già scritti dall'applicazione (conto registrato, flusso creato, ...) diventano visibili.
