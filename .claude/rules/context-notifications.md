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

## Porte del contesto

Repository delle chat collegate e dei codici, invio dei messaggi, ricezione dei messaggi al bot.
