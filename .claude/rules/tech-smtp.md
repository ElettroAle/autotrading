---
paths:
  - "src/autotrading/adapters/outbound/smtp/**"
  - "tests/unit/adapters/smtp/**"
---

# Adapter in uscita: SMTP (server di posta del tenant)

Decisioni in ADR invio-dal-server-di-posta-del-tenant e ADR server-di-posta-per-tenant (sostituiscono, per la
provenienza del server, ADR canale-email-delle-notifiche-con-smtp).

- Il sistema integrato è il server di posta che ogni tenant indica nella dashboard, raggiunto con `smtplib` ed
  `email.message` della libreria standard: nessuna libreria esterna, nessun SDK di un fornitore. Nessuna altra
  cartella invia email.
- Nessuna configurazione dell'installazione: niente `SMTP_*`, niente `configuration.py`. `SmtpMailerAdapter`
  realizza `MailerPort` e riceve a ogni invio il `MailServer` del tenant e la password già aperta dal worker.
- Una connessione per email: sicurezza `TLS` con `SMTP_SSL`, `STARTTLS` con `SMTP` + `starttls`, sempre con un
  contesto TLS che verifica certificato e nome del server; login con utente e password.
- `smtplib.SMTPAuthenticationError` diventa `MailServerRefusedLoginError ... from error`; gli altri
  `smtplib.SMTPException` e `OSError` diventano `EmailNotDeliveredError ... from error`: la permanenza resta
  all'errore base.
- Solo il worker compone il mailer; l'`api` non invia email e non apre la password.
- La password non compare in log, errori o `repr`.
