---
paths:
  - "src/autotrading/*/notifications/**"
  - "tests/**/notifications/**"
  - "specs/E1-flussi-autonomi/F1.8-notifiche/**"
---

# Contesto notifications

Le notifiche all'utente su Telegram.

## Glossario

- **Linked chat**: chat Telegram collegata a un tenant; al massimo una per tenant, un nuovo collegamento
  sostituisce il precedente (R1.8.1).
- **Link code**: codice monouso valido 15 minuti, inviato dall'utente al bot dalla propria chat.
- **Notification**: evento del flusso o del conto con i valori essenziali: apertura, chiusura, ciclo
  fallito, ordine rifiutato, pausa automatica, non attribuibile (R1.8.2).

## Regole

- Un solo bot della piattaforma, in long polling: nessuna porta in ingresso. Il token del bot è un file
  montato in sola lettura, mai una variabile d'ambiente.
- Una notifica va solo alla chat collegata al tenant e non contiene mai credenziali.
- Un invio che fallisce si registra e non fa fallire il ciclo. Senza chat collegata non si invia nulla.
- La risposta a un codice scaduto, già usato o inesistente è la stessa e non rivela se il codice è esistito.
- Il codice si salva solo come digest; il bot trova il tenant dal digest e riscatta il codice con le porte
  legate a quel tenant. Il bot gira nel worker; senza token le notifiche sono disattivate, mai un errore
  di avvio (ADR 0035).
- Il codice si legge da solo o dopo il comando di avvio; un messaggio senza codice, o un altro comando,
  riceve le istruzioni per il collegamento, mai "codice non valido" (Bug 163).
- Il comando `/prova` (anche `/prova@<bot>`) dalla chat collegata invia una notifica di prova con il
  `NotifyUseCase` di ogni tenant collegato alla chat; da una chat non collegata riceve le istruzioni. Il bot
  trova i tenant dalla chat con `LinkedChatLookupPort`, unica lettura delle chat prima del tenant (ADR 0081).
- Il codice arriva con il link `t.me/<bot>?start=<codice>`; il nome del bot si chiede a Telegram (`getMe`)
  nel worker, l'API lo chiede al worker; senza bot attivo il link è assente e il codice vale lo stesso
  (ADR 0072).

## Porte del contesto

Repository delle chat collegate e dei codici, ricerca dei tenant di una chat (`LinkedChatLookupPort`), invio dei messaggi, ricezione dei messaggi al bot, nome del
bot (`BotIdentityPort`).
