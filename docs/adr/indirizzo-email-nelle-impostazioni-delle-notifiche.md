# ADR indirizzo-email-nelle-impostazioni-delle-notifiche — Indirizzo email nelle Impostazioni delle notifiche

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.5.2 (468), Task T3.5.2.2 (493)
- Collegate: ADR canale-email-delle-notifiche-con-smtp, ADR 0116 (dashboard fuori dall'esagono), ADR 0118 (accesso
  Entra della dashboard)

## Contesto e problema

La pagina Notifiche della dashboard (`src/app/routes/app/notifications.tsx`) mostra oggi solo la sezione Telegram
(`LinkedChatPanel`, `LinkCodePanel`). R3.5.2 chiede di indicare, cambiare e togliere l'indirizzo email, chiedere
un'email di prova e vedere l'avviso quando il servizio di posta manca.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile
  (pannelli, campi e messaggi di stato già usati nelle Impostazioni, `src/components/ui`), nessun duplicato per pagina.
- `.claude/rules/tech-dashboard.md`: bulletproof-react, una funzionalità per cartella, chiamate in `api/` con
  TanStack Query, nessuna logica che l'API non esponga.
- API dell'ADR canale-email-delle-notifiche-con-smtp: `GET/PUT/DELETE /notifications/email`,
  `POST /notifications/email/test`; l'avviso arriva già scritto dall'API.

## Opzioni considerate

1. Nella funzionalità `notifications` esistente: `api/get-notification-email.ts`, `set-notification-email.ts`,
   `remove-notification-email.ts`, `send-test-email.ts` e un componente `NotificationEmailPanel` (campo con etichetta
   «Indirizzo email», comandi Salva, Togli, Invia email di prova, avviso dell'API in un messaggio di stato, errori di
   validazione dell'API sotto il campo). La pagina aggiunge la sezione «Notifiche email» sotto quella Telegram, con
   gli stessi elementi di layout e di stato della sezione Telegram.
2. Una funzionalità nuova `notification-email`: scartata, è lo stesso contesto delle notifiche e duplicherebbe
   struttura e pannelli.

## Esito della decisione

Opzione 1. La validazione della forma resta all'API (un solo punto); il campo usa `type="email"` solo per la tastiera
del telefono. Su schermo stretto la sezione segue il layout a colonna delle Impostazioni (F6.4).

Verifica: prova (unit test del pannello con API finta: indirizzo mostrato, salvataggio, rimozione, prova, avviso,
errore di validazione). Gli scenari di R3.5.2 si eseguono con pytest-bdd sui casi d'uso: le feature di E3 non sono
nell'elenco di playwright-bdd.

### Conseguenze

- La pagina Notifiche raccoglie entrambi i canali; R3.5.3 vi aggiungerà la scelta per tipo di evento.
