# ADR canali-delle-notifiche-come-insieme — La scelta dei canali è un insieme di canali

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 578, Task 579; R3.5.3 (scelta dei canali)
- Collegate: ADR scelta-dei-canali-nella-dashboard, ADR invio-dal-server-di-posta-del-tenant
- Verifica: prova

## Contesto e problema

`NotificationChannel` (`domain/notifications/notification_channel.py:87-95`) elenca combinazioni: `TELEGRAM`, `EMAIL`,
`BOTH`, `NONE`. Con un terzo canale le combinazioni crescono in modo esponenziale e ogni punto che le interpreta
(`reaches_chat`, `reaches_email`, `missing_links`, API, CHECK della tabella, dashboard) va riscritto. Il proprietario
(17/11/2026): «vanno messi dei flag sul canale, che dipende dalla lista di adapter disponibili dietro a
quell'interfaccia. Altrimenti è immanutenibile».

## Fattori decisionali

- Decisione del proprietario (17/11/2026), Bug 578.
- Un canale nuovo deve richiedere solo il suo membro, il suo adapter e la sua condizione di disponibilità.
- La migrazione conserva le scelte esistenti.

## Decisione

- Domain: `NotificationChannel` diventa l'elenco dei canali (`TELEGRAM`, `EMAIL`); la scelta di un evento è
  `frozenset[NotificationChannel]` (vuoto = nessuna notifica). `ChannelPreferences` conserva scelte ed eccezioni per
  flusso come insiemi; i predefiniti diventano `{TELEGRAM}` e insieme vuoto per le decisioni ridotte o bloccate.
  `missing_links` lavora per canale.
- Application: `NotifyUseCase` accoda un messaggio per ogni canale dell'insieme che è disponibile; la disponibilità di
  ogni canale è una funzione del canale (chat collegata; indirizzo e server di posta), non delle combinazioni. La
  notifica di prova va a tutti i canali disponibili.
- SQLAlchemy: migrazione dopo l'ultima di main: colonna `channels TEXT[]` con CHECK che ogni elemento sia un canale noto,
  dati convertiti (`telegram`→`{telegram}`, `email`→`{email}`, `both`→`{telegram,email}`, `none`→`{}`), colonna
  `channel` rimossa, in entrambe le tabelle; downgrade inverso.
- API: `channels: list[str]` al posto di `channel` in lettura e scrittura; `GET` elenca anche i canali con il loro stato
  (configurato o cosa manca).
- Scenari R3.5.3 riallineati agli insiemi (stessi casi, con «Telegram ed email» al posto di «entrambi»).

## Alternative scartate

- Aggiungere combinazioni all'enum: esattamente ciò che il proprietario esclude.

## Conseguenze

- Un canale nuovo è un membro dell'enum, il suo adapter e la sua disponibilità.
