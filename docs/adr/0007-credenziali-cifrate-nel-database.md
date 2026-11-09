# ADR 0007 — Credenziali dei conti cifrate nel database

- Stato: accettata (9 novembre 2026)
- Requisiti: R0.2.1, R0.2.3, R0.2.4, R0.2.5, R0.2.6

## Contesto

L'architettura dell'8 novembre custodiva le credenziali dei conti in OpenBao: un container in più con
storage raft, sblocco da file, AppRole per servizio, OIDC per le persone e un ruolo applicativo
`Gestore chiavi` per amministrarlo. Per un'installazione a nodo singolo, su una macchina piccola e
con un solo utente, è molto da far girare e da mantenere, e lega l'hosting a una macchina in grado di
ospitarlo. I segreti nativi di Docker Compose non bastano: sono file fissi decisi al deploy, mentre
le credenziali le inserisce l'utente mentre la piattaforma gira, una per conto.

I vincoli del proprietario restano: le credenziali dei conti le leggono solo identità di servizio,
mai persone; mai segreti in variabili d'ambiente.

## Decisione

- **Cifratura asimmetrica** con libsodium (PyNaCl, `SealedBox`): una coppia di chiavi per
  installazione.
  - Chi salva le credenziali (`api`) ha **solo la chiave pubblica**: cifra, non può decifrare.
  - La **chiave privata** l'ha **solo il `worker`**: file leggibile solo da root sul server, montato
    in sola lettura nel solo container `worker`.
- **Formato salvato** nel database, accanto al conto: versione della chiave e testo cifrato. Il testo
  cifrato contiene anche tenant e conto, che la decifratura confronta con il conto richiesto: una
  credenziale copiata su un altro conto è rifiutata.
- **Generazione delle chiavi sul server**: la pipeline genera la coppia sulla macchina al primo
  deploy, se assente. La chiave privata non passa da GitHub né da una persona.
- **Porte**: `SecretVaultPort` è sostituita da `CredentialSealerPort` (cifra) e
  `CredentialOpenerPort` (decifra) in `application/accounts/ports.py`, implementate in
  `adapters/outbound/libsodium/`. Il testo cifrato lo salva `AccountRepositoryPort`. Le due porte
  separate fanno sì che `api` riceva solo la prima.
- **Funzioni che usano credenziali salvate** (stato del conto R0.2.2, ordini R0.3) arrivano con il
  `worker`. Registrazione e sostituzione (R0.2.1, R0.2.4) verificano le credenziali presenti nella
  richiesta prima di cifrarle, quindi non decifrano nulla.
- **Segreti dei servizi** (password del database, chiavi dei fornitori dei modelli): file montati in
  sola lettura, consegnati dalla pipeline dai segreti degli environment GitHub.
- **Ruolo `Gestore chiavi` tolto.** In emergenza si revoca l'API wallet dal wallet principale
  sull'exchange (playbook in `docs/architecture.md` §8.2).
- **Nessuna rotazione per ora.** La versione della chiave è nel formato fin dall'inizio, così la
  rotazione dalla pipeline (R0.2.6, requisito futuro) non richiede migrazioni del formato.

## Alternative scartate

- **OpenBao**: un servizio in più con sblocco, storage e identità da gestire; più adatto quando
  servono audit e policy per identità su molti segreti.
- **Cifratura simmetrica con chiave unica**: anche `api` potrebbe decifrare, contro la regola che
  la riserva al servizio che opera sull'exchange.
- **Un secret Docker o Kubernetes per tenant**: Compose non crea secret mentre l'applicazione gira;
  in Kubernetes servirebbe un service account con permesso di creare Secret e chi amministra il
  cluster li leggerebbe.
- **KMS di un provider cloud**: lega l'architettura a un provider e aggiunge un costo.

## Conseguenze

- Un container in meno, nessuno sblocco e nessuna identità da gestire per l'archivio.
- Si perde l'audit delle letture di OpenBao: la decifratura si registra nel registro applicativo
  (conto e momento, mai il contenuto).
- La perdita della chiave privata rende illeggibili le credenziali salvate: l'utente le rigenera
  sull'exchange e le reinserisce (R0.2.4). Nessun denaro è coinvolto.
- Il modello di minaccia non cambia: contro root sulla macchina in esecuzione nessuno schema su nodo
  singolo protegge ciò che è in uso.
- Nuova dipendenza PyNaCl, importata solo in `adapters/outbound/libsodium/`.
