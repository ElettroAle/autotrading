# ADR campanello-delle-notifiche-nella-dashboard — Campanello in alto a destra con le notifiche del tenant

- Stato: proposta (19 novembre 2026)
- Requisiti: US 380 R6.2.1, Task 382; dipende da Task 381
- Collegate: ADR notifiche-nell-app-salvate-per-tenant, ADR area-utente-in-alto-a-destra, ADR
  intestazione-su-una-riga, ADR pagina-avvisi-nella-dashboard, ADR icone-con-lucide-react-e-comandi-condivisi;
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

L'intestazione (`components/layouts/app-header.tsx`) ha a destra il badge dell'ambiente e `UserMenu`. R6.2.1 chiede un
campanello accanto al nome con il numero delle non lette e l'elenco con il collegamento alla pagina interessata.

## Fattori decisionali

- Regole della dashboard: il codice condiviso non importa le funzionalità; l'intestazione è condivisa. Il conteggio
  degli avvisi del menu segue lo stesso schema (`hooks/use-open-alerts-count.ts`, dati della pagina riletti con la
  pagina, R2.1.2).
- Intestazione su una riga a ogni larghezza (ADR intestazione-su-una-riga); icone solo da `components/ui/icons`.
- Accessibilità: il numero non si legge solo dal colore; il pannello si apre e si chiude da tastiera.

## Decisione

- `hooks/use-unread-notifications-count.ts`: `GET /notifications/inbox/summary` come dato della pagina, sotto la
  chiave `notifications`.
- `components/layouts/notification-bell.tsx` in `AppHeader`, tra il badge dell'ambiente e `UserMenu`: pulsante con
  icona campanello (nuova icona condivisa `bell`), nome accessibile «Notifiche, N non lette», numero in un pallino
  solo quando ci sono non lette (oltre 99 «99+»). Apre un pannello sotto l'intestazione, largo al più 24rem e su
  telefono quanto lo schermo meno i margini, con l'elenco dalla più recente (icona, titolo, testo, data e ora) e
  «Segna tutte come lette»; si chiude con Esc o con un clic fuori. Le non lette sono in grassetto con un punto.
- Scegliere una notifica la segna letta e porta alla prima destinazione, con il percorso della dashboard costruito da
  `config/paths` per tipo (flusso, operazione, avviso); senza destinazione la segna solo letta.
- Il pannello mostra le prime 20; «Mostra altre» legge la pagina seguente.
- Scenari R6.2.1 della dashboard con Playwright sul finto MSW, che tiene le notifiche nella piattaforma finta.

## Alternative scartate

- Una pagina Notifiche separata al posto del pannello: R6.2.1 chiede un campanello che si apre accanto al nome.
- Il campanello dentro una funzionalità: l'intestazione condivisa non può importarla.

## Conseguenze

- Una richiesta in più a ogni rilettura della pagina, come il conteggio degli avvisi.
