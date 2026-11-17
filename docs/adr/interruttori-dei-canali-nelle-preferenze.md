# ADR interruttori-dei-canali-nelle-preferenze — Un interruttore per canale nella riga dell'evento

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 578, Task 580; R3.5.3
- Collegate: ADR canali-delle-notifiche-come-insieme, ADR pagina-notifiche-a-schede, `.claude/rules/tech-dashboard.md`
  §Pagine di impostazioni
- Verifica: prova

## Contesto e problema

`NotificationChannelsPanel` (`features/notifications/components/notification-channels-panel.tsx`) usa per ogni evento
un `<select>` con Telegram, email, entrambi, nessuno. Il proprietario (17/11/2026) ha scelto interruttori nella riga.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): «A. Interruttori nella riga»; la pagina non deve rompersi con più canali.
- Regole UX: stato visibile con icona e testo, rimando «Configura» alla scheda Canali.

## Decisione

- Per ogni evento, nella riga, un pulsante a interruttore per canale (`aria-pressed`, icona e nome del canale) che va a
  capo se i canali non stanno; su telefono una card per evento con gli stessi interruttori. Un canale non configurato
  è disattivato con il motivo e il collegamento «Configura» alla scheda Canali.
- Eccezioni per flusso con gli stessi interruttori più «Come la scelta generale» per togliere l'eccezione.
- Salvataggio a ogni interruttore con `channels`; errori mostrati con `FormAlert`.
- Prove: unit test del pannello (attiva, disattiva, canale non configurato, eccezione) e layout a 360 e 1280 px.

## Alternative scartate

- Colonne per canale in una tabella: si rompe con molti canali.

## Conseguenze

- Un canale nuovo appare come un interruttore in più senza cambiare il pannello.
