# ADR notifica-strutturata-con-icona-titolo-e-valori — Notifica strutturata con icona, titolo e valori

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.4 (533), Task T3.5.4.1 (534); R1.8.2, R3.5.1
- Collegate: ADR eventi-notificabili-di-rischio-e-capitale, ADR canale-email-delle-notifiche-con-smtp, ADR 0092
  (notifiche come passi dei casi d'uso), ADR 0070 (ogni chiusura notificata con il PnL dell'exchange)

## Contesto e problema

Oggi una `Notification` (`domain/notifications/notification.py`) ha solo il soggetto e l'evento, e diventa la riga
«soggetto: evento, dettagli». Il proprietario la trova illeggibile: «Notifiche Telegram più chiare e con icone che
evidenziano l'accaduto altrimenti non si capisce cosa accade». R3.5.4 chiede icona per tipo di evento, titolo con
flusso ed evento, valori uno per riga e, per le notifiche di un flusso, lo stato del flusso in fondo.

## Fattori decisionali

- Decisioni del proprietario (16/11/2026): icone che evidenziano l'accaduto; lo stato del flusso «in ogni notifica»;
  gli scostamenti sotto soglia restano notificati tutti, «tutti, come oggi».
- R3.5.4: le icone dell'elenco del requisito; l'email ha per oggetto il titolo e lo stesso contenuto; le notifiche non
  legate a un flusso (prova, eventi del conto) non hanno lo stato del flusso.
- ADR eventi-notificabili-di-rischio-e-capitale: ogni `Notification` porta il suo tipo di evento (`NotificationEvent`)
  per la scelta dei canali di R3.5.3; questo ADR usa lo stesso tipo per l'icona.
- `CLAUDE.md`: le regole sui valori stanno nel domain; nomi espressivi.

## Opzioni considerate

1. **Notifica strutturata nel domain.** `Notification` diventa: `event: NotificationEvent`, `subject` (flusso o
   conto), `headline` (l'evento in parole, per esempio «posizione aperta»), `lines: tuple[NotificationLine, ...]`
   (etichetta e valore, per esempio «Asset: BTC», «Direzione: long», «Leva: 3», «Valore: 150 USDC») e
   `flow_status: FlowStatusLine | None` (ADR stato-del-flusso-in-ogni-notifica). L'icona la decide il domain dal tipo
   di evento e, per le chiusure, dall'esito:
   - 🟢 apertura;
   - ✅ chiusura in profitto (PnL > 0), 🔻 chiusura in perdita (PnL ≤ 0);
   - 🛑 stop loss, 🎯 take profit;
   - ⚠️ ciclo fallito e ordine rifiutato;
   - ⏸️ pausa e aperture sospese, ▶️ ripresa, ⏹️ stop del flusso;
   - 🚨 allarmi e movimenti non attribuibili.

   Gli eventi di R3.5.1 senza icona nel requisito prendono quella della famiglia: riduzione o blocco dal rischio ⚠️,
   liquidazione 🔻, incasso ✅, emergenza 🚨. Il titolo è `f"{icona} {soggetto}: {headline}"`. Ogni fabbrica
   (`position_opened`, `position_closed`, `cycle_failed`, ... e quelle nuove di R3.5.1) produce le sue righe. Il testo
   resta una proprietà del domain: `title`, `body_lines()` (righe dei valori e, se c'è, la riga dello stato) e `text`
   (titolo, riga vuota, corpo).
2. Template di testo negli adapter Telegram e SMTP: scartata, duplicherebbe le regole del contenuto in due cartelle e
   il contenuto deve essere lo stesso nei due canali (R3.5.4).
3. Testo libero con l'icona davanti: scartata, i valori non vanno a capo e lo stato del flusso non ha un posto fisso.

## Esito della decisione

Opzione 1. `email_subject` diventa il titolo, così l'oggetto è «🟢 alfa: posizione aperta». Il separatore
`DETAILS_SEPARATOR` sparisce, perché i dettagli sono righe. Gli scenari di R1.8.2 e R3.5.1 che verificano il testo
delle notifiche (frasi «contiene "alfa: chiusa BTC ..."») si riallineano al nuovo formato, titolo e valori, con lo
stesso significato: i `.feature` e i criteri sulla board delle User Story toccate si aggiornano nella stessa PR.

Verifica: prova (unit test delle fabbriche e dell'icona per tipo ed esito; scenari di R3.5.4 «Posizione aperta»,
«Icona per evento» e «Notifica senza flusso»).

### Conseguenze

- Un tipo di evento nuovo dichiara icona, titolo e righe nella sua fabbrica: nessun canale cambia.
- Il formato è lo stesso per Telegram, email e il campanello futuro (R6.2.1).
