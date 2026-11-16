# ADR canali-delle-notifiche-per-tipo-di-evento — Canali delle notifiche per tipo di evento ed eccezioni per flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.5.3 (469), Task T3.5.3.1 (494); RF-24.04
- Collegate: ADR eventi-notificabili-di-rischio-e-capitale, ADR canale-email-delle-notifiche-con-smtp

## Contesto e problema

Dopo R3.5.1 e R3.5.2 ogni notifica va a tutti i canali collegati. R3.5.3 chiede una scelta per tipo di evento
(Telegram, email, entrambi, nessuno), con predefiniti e con eccezioni per flusso, e un avviso quando il canale scelto
non è collegato.

## Fattori decisionali

- Decisione del proprietario (E3): canali scelti per tipo di evento con eccezioni per flusso.
- R3.5.3: predefinito «nessuno» per decisione ridotta e bloccata dal rischio, «Telegram» per gli altri; gli eventi
  del conto non hanno eccezioni.
- `.claude/rules/tech-sqlalchemy.md`: dati posseduti con RLS.

## Opzioni considerate

1. Domain: `NotificationChannel` (`TELEGRAM`, `EMAIL`, `BOTH`, `NONE`), `ChannelPreferences(TenantOwned)` con la
   scelta generale per tipo di evento e le eccezioni per flusso; `channel_for(event, flow_id)` applica eccezione,
   scelta generale, predefinito; un'eccezione su un evento del conto solleva
   `AccountEventWithoutFlowExceptionError("<evento> è un evento del conto: segue la scelta generale")`.
   Application: porta `ChannelPreferencesRepositoryPort`, casi d'uso `ChooseNotificationChannelUseCase`,
   `SetFlowChannelExceptionUseCase`, `RemoveFlowChannelExceptionUseCase`, `GetNotificationChannelsUseCase` (con gli
   avvisi «Telegram non collegato» e «email non indicata»); `NotifyUseCase` accoda solo sui canali di
   `channel_for`. SQLAlchemy: tabelle `notification_channels` e `notification_channel_exceptions` con RLS. API:
   `GET/PUT /notifications/channels`, `PUT/DELETE /notifications/channels/flows/{flow_id}/{event}`.
2. Preferenze come JSON libero sul tenant: scartata, perde la validazione nel domain.

## Esito della decisione

Opzione 1. Si sviluppa dopo R3.5.1 e R3.5.2.

Verifica: prova (scenari di R3.5.3; unit test di `channel_for`; test di integrazione delle tabelle con RLS).

### Conseguenze

- Il campanello (R6.2.1) resta fuori dalla scelta e riceve ogni notifica.
