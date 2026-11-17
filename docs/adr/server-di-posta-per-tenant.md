# ADR server-di-posta-per-tenant — Server di posta per tenant con password sigillata

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.5, Task T3.5.5.1; RF-24.01, RF-01.05
- Collegate: ADR 0007 (credenziali cifrate nel database), ADR 0029 (chiavi dei fornitori IA), ADR
  canale-email-delle-notifiche-con-smtp (sostituita per la sola provenienza del server), ADR
  indirizzo-email-nelle-impostazioni-delle-notifiche
- Verifica: prova

## Contesto e problema

Il canale email (R3.5.2) usa oggi un servizio di posta dell'installazione (`SMTP_*` e un file della password). Il
proprietario vuole che il server lo indichi ogni utente dalla dashboard, come collega la chat Telegram, senza nulla
nell'installazione (decisione del 17/11/2026). Serve decidere dove vive il server e come si protegge la password.

## Fattori decisionali

- RF-01.05: le credenziali dei servizi di un utente stanno nel suo tenant e si usano solo per i suoi flussi.
- ADR 0007, CLAUDE.md §Sicurezza: le credenziali le legge solo un'identità di servizio, cifrate nel database e
  decifrabili solo dal `worker`; l'API cifra con la chiave pubblica e non decifra mai.
- ADR 0029: lo stesso schema per le chiavi dei fornitori IA (testo sigillato che nomina tenant e servizio).
- Multi-tenancy: ogni dato è `TenantOwned`, RLS in PostgreSQL.

## Decisione

- Domain (`domain/notifications`): `MailServer` (`TenantOwned`, frozen) con `host`, `port` (1-65535), `security`
  (`MailSecurity`: `STARTTLS` | `TLS`), `username`, `sender` (se vuoto, `username`; forma di un indirizzo email) e
  `SealedMailPassword` (versione della chiave e byte sigillati). Gli errori di forma portano il valore rifiutato.
- Application (`application/notifications`): porte `MailServerRepositoryPort` (`get`, `save`, `remove`),
  `MailPasswordSealerPort` (`seal(password) -> SealedMailPassword`), `MailPasswordOpenerPort`
  (`open(sealed) -> str`, solo nel worker). Casi d'uso `SetMailServerUseCase` (una modifica senza password conserva
  quella salvata; il primo salvataggio la richiede), `GetMailServerUseCase` (mai la password: solo `password_saved`),
  `RemoveMailServerUseCase`.
- Adapter `libsodium/`: `SodiumMailPasswordSealerAdapter` e `SodiumMailPasswordOpenerAdapter`, legati al tenant; il
  testo sigillato nomina il tenant, così l'opener rifiuta una password copiata su un altro tenant (come ADR 0029).
- Adapter `sqlalchemy/`: tabella `notification_mail_servers` (`tenant_id` chiave, colonne del server,
  `sealed_password`, `key_version`) con RLS FORCE e policy; migrazione dopo l'ultima di main.
- API (`inbound/api`): `GET`/`PUT`/`DELETE /notifications/mail-server`; la risposta non contiene mai la password.

## Alternative scartate

- Server unico dell'installazione da variabili: escluso dal proprietario.
- Server unico inserito da un amministratore: non esiste un ruolo amministratore; scartato dal proprietario.
- Password in chiaro nel database: viola ADR 0007.

## Conseguenze

- Ogni utente usa il proprio servizio (es. una casella con password per le app), senza costi per la piattaforma.
- La password resta nel tenant, sigillata; solo il worker la apre, nel momento dell'invio.
