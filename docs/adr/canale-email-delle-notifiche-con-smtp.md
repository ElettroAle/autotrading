# ADR canale-email-delle-notifiche-con-smtp — Canale email delle notifiche con SMTP

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.5.2 (468), Task T3.5.2.1 (492); RF-24.02
- Collegate: ADR outbox-delle-integrazioni-esterne-con-procrastinate, ADR ritentativi-dell-outbox-in-circa-sei-ore,
  ADR permanenza-decisa-dall-errore-base, ADR 0092 (notifiche come passi dei casi d'uso), ADR 0134 (prova delle
  notifiche dall'API), ADR 0089 (un adapter, una tecnologia)

## Contesto e problema

Le notifiche oggi partono solo verso la chat Telegram del tenant, attraverso l'outbox (`OutboxMessage.to_chat`,
consegnato dal worker con `DeliverOutboxMessageUseCase`). R3.5.2 aggiunge un secondo canale: un indirizzo email per
tenant, senza verifica, con un'email di prova, e il canale non disponibile quando l'installazione non ha un servizio di
posta. Serve decidere dove vive l'indirizzo, quale sistema invia le email e come l'invio passa per l'outbox.

## Fattori decisionali

- Decisioni del proprietario (E3): email senza verifica dell'indirizzo; canali per tipo di evento con eccezioni per
  flusso (R3.5.3, dopo); nessuna spesa; mai segreti in variabili d'ambiente, solo file montati in sola lettura.
- `CLAUDE.md`: un adapter = una tecnologia (il sistema integrato è il server di posta); configurazione per adapter in
  `configuration.py` e `composition.py`; la permanenza la decide l'errore base; le porte stanno nel contesto che le
  usa.
- ADR outbox: ogni messaggio verso un sistema esterno passa per l'outbox generico per integrazione; un invio fallito si
  ritenta per circa sei ore.
- `.claude/rules/tech-sqlalchemy.md`: ogni tabella di dati posseduti ha `tenant_id` e RLS forzata.
- `.claude/rules/context-notifications.md`: una notifica non contiene mai credenziali e va solo al tenant dell'evento.

## Opzioni considerate

1. **SMTP con `smtplib` della libreria standard**, in una cartella `adapters/outbound/smtp/`: funziona con qualunque
   servizio di posta (anche gratuito, o un relay dell'installazione) senza SDK di un fornitore; nessuna libreria nuova.
2. API HTTP di un fornitore (SendGrid, Mailgun, Resend): scartata, lega il codice a un fornitore e quasi sempre a un
   account a pagamento o con dati personali del proprietario.
3. Email inviata dall'`api` subito, fuori dall'outbox: scartata, contraddice l'ADR dell'outbox.

## Esito della decisione

Opzione 1.

**Domain** (`domain/notifications/`):

- `EmailAddress`: value object; forma `^[^@\s]+@[^@\s]+\.[^@\s]+$` dopo `strip`, altrimenti
  `InvalidEmailAddressError("indirizzo email non valido")` (400).
- `NotificationEmail(TenantOwned)`: l'indirizzo delle notifiche del tenant, uno per tenant.
- `Notification.email_subject`: `"<soggetto>: <evento senza i dettagli>"`, cioè il testo dell'evento fino alla prima
  `", "` (`"alfa: in pausa"` per l'evento `"in pausa, credito esaurito"`); il testo dell'email è `Notification.text`.
  `Notification.test()` ha oggetto email `"AutoTrading: prova delle notifiche"`.
- `OutboxMessage.to_email(address, subject, text)`: integrazione `EMAIL_MESSAGE = "email_message"`, payload
  `{to, subject, text}`; `email_message()` lo rilegge o solleva `InvalidOutboxMessageError`.

**Application** (`application/notifications/`):

- Porte in `ports.py`: `NotificationEmailRepositoryPort` (`get`, `set`, `remove`, legata al tenant), `MailerPort`
  (`send(address, subject, text)`, solleva `MessageNotDeliveredError`, temporaneo), `MailServicePort`
  (`is_configured() -> bool`).
- Casi d'uso: `SetNotificationEmailUseCase`, `RemoveNotificationEmailUseCase`, `GetNotificationEmailUseCase`
  (restituisce l'indirizzo, o nessuno, e l'avviso `"le email non partono: servizio di posta non configurato"` quando
  il servizio manca), `SendTestEmailUseCase` (senza indirizzo `NoNotificationEmailToTestError`; senza servizio
  `MailServiceNotConfiguredError("servizio di posta non configurato")`, 409; altrimenti accoda l'email di prova).
- `NotifyUseCase` riceve anche `NotificationEmailRepositoryPort` e `MailServicePort`: accoda il messaggio della chat
  come oggi e, se il tenant ha un indirizzo e il servizio è configurato, un `OutboxMessage.to_email`. Fino a R3.5.3
  ogni notifica va su tutti i canali collegati; R3.5.3 introdurrà la scelta per tipo di evento in questo stesso caso
  d'uso. Il passo «canale email scelto per l'evento» del Contesto di R3.5.2 non ha effetto fino ad allora.
- `DeliverOutboxMessageUseCase` riceve `MailerPort` e aggiunge `EMAIL_MESSAGE: self._send_email`, con lo stesso
  trattamento dell'invio alla chat (avviso nel log, `MessageNotDeliveredError` rilanciato perché l'outbox ritenti).

**Adapter `adapters/outbound/smtp/`** (nuova tecnologia: il server di posta; libreria standard `smtplib` ed
`email.message`, nessuna libreria esterna; voce `"adapters/outbound/smtp": frozenset()` in `TECHNOLOGY_LIBRARIES`):

- `configuration.py`: `_SmtpSettings` (frozen) letta con `optional`: `SMTP_HOST`, `SMTP_PORT` (587 se assente),
  `SMTP_USERNAME`, `SMTP_SENDER` (obbligatorio se c'è l'host), e la password con `optional_secret` dal file
  `SMTP_PASSWORD_FILE`. Senza host il servizio non è configurato.
- `SmtpMailerAdapter`: porta 465 con `SMTP_SSL`, altrimenti `SMTP` + `starttls`; login se c'è l'utente; traduce
  `smtplib.SMTPException` e `OSError` in `MessageNotDeliveredError ... from error` (la permanenza resta all'errore
  base: un rifiuto SMTP non ha `status_code` HTTP e resta temporaneo come dichiarato).
- `SmtpMailServiceAdapter.is_configured()`; senza host `SmtpDisabledMailerAdapter` fa fallire ogni invio con
  `MessageNotDeliveredError`.
- `composition.py`: `smtp_adapters(source)` per il worker (mailer e servizio) e `smtp_service_adapters(source)` per
  l'`api` (solo il servizio, dalle impostazioni non segrete: l'`api` non monta la password).
- La password non compare in log, errori o `repr`. Nuova rule `.claude/rules/tech-smtp.md`; `smtp/` entra
  nell'elenco delle cartelle e nell'indice delle rule di `CLAUDE.md`; nuovo contratto di indipendenza in
  `pyproject.toml`.

**SQLAlchemy**: tabella `notification_emails` (`tenant_id` chiave primaria, `address`, `updated_at`) con RLS forzata,
migrazione Alembic, `SqlAlchemyNotificationEmailRepositoryAdapter`, test di integrazione su PostgreSQL vero.

**API** (`adapters/inbound/api/notification_email.py`): `GET /notifications/email` (indirizzo e avviso),
`PUT /notifications/email` (`{address}`), `DELETE /notifications/email`, `POST /notifications/email/test` (202);
errori in Problem Details dall'handler centrale.

**Bootstrap**: `notify_for` passa anche l'adapter dell'indirizzo e il servizio; il worker crea il mailer con
`smtp_adapters(source)`; nessuna decisione.

**Deploy**: nessuna variabile nuova obbligatoria; senza `SMTP_HOST` l'installazione non ha il canale email e resta
così finché il proprietario non sceglie un servizio di posta.

Verifica: prova (scenari pytest-bdd di R3.5.2 sui casi d'uso con `FakeMailerAdapter`; unit test di domain, casi
d'uso e adapter SMTP con un server SMTP finto in memoria; test di integrazione della tabella con RLS; test di
architettura).

### Conseguenze

- Il canale email funziona con qualunque servizio SMTP senza codice nuovo; finché non c'è un servizio configurato
  l'indirizzo si salva e la dashboard avvisa.
- R3.5.3 aggiungerà la scelta dei canali in `NotifyUseCase` senza toccare l'adapter.
- Il campanello (R6.2.1), quando arriverà, resta fuori da questa scelta.
