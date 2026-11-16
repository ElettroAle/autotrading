---
paths:
  - "src/autotrading/adapters/outbound/smtp/**"
  - "tests/unit/adapters/smtp/**"
---

# Adapter in uscita: SMTP (servizio di posta)

Decisione in ADR canale-email-delle-notifiche-con-smtp.

- Il sistema integrato è il servizio di posta dell'installazione, raggiunto con `smtplib` ed `email.message` della
  libreria standard: nessuna libreria esterna, nessun SDK di un fornitore. Nessuna altra cartella invia email.
- `SmtpMailerAdapter` realizza `MailerPort`: una connessione per email; porta 465 con `SMTP_SSL`, ogni altra porta
  con `SMTP` + `starttls`; login solo se c'è l'utente. `smtplib.SMTPException` e `OSError` diventano
  `EmailNotDeliveredError ... from error`: la permanenza resta all'errore base.
- `SmtpMailServiceAdapter` realizza `MailServicePort`. Senza `SMTP_HOST` il servizio non è configurato:
  `SmtpDisabledMailerAdapter` fa fallire ogni invio, che si registra senza fermare i flussi.
- `configuration.py`: `_SmtpSettings` da `SMTP_HOST`, `SMTP_PORT` (587 se assente), `SMTP_SENDER` (obbligatorio se
  c'è l'host), `SMTP_USERNAME` e la password dal file `SMTP_PASSWORD_FILE` (obbligatorio se c'è l'utente). **Mai
  variabili d'ambiente per la password.**
- `composition.py`: `smtp_adapters(source)` per il worker (mailer e servizio), `smtp_service_adapters(source)` per
  l'`api` (solo il servizio, dalle impostazioni non segrete: l'`api` non monta la password).
- La password non compare in log, errori o `repr`.
