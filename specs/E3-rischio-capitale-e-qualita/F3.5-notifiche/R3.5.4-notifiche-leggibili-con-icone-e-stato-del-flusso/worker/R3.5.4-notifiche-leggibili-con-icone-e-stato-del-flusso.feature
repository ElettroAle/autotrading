# language: it
@R3.5.4
Funzionalità: R3.5.4 Notifiche leggibili con icone e stato del flusso
  Come utente
  Voglio notifiche che dicano subito cosa è successo e come sta il flusso
  Perché oggi da una riga di testo non capisco cosa accade

  Ogni notifica ha un'icona che dice il tipo di evento, un titolo con flusso ed evento, i valori dell'evento uno per
  riga e, in fondo, lo stato del flusso: valore, PnL dall'avvio, posizioni aperte e stato. Lo stato del flusso c'è
  in ogni notifica di un flusso. L'email usa lo stesso contenuto (oggetto dal titolo). Le notifiche non legate a un
  flusso (prova, allarmi del conto) hanno icona e titolo senza lo stato del flusso.
  Icone: 🟢 posizione aperta, ✅ chiusa in profitto, 🔻 chiusa in perdita, 🛑 stop loss, 🎯 take profit, ⚠️ ciclo
  fallito, ⏸️ flusso in pausa, 🚨 allarme. Gli eventi sono quelli di R1.8.2 e R3.5.1.

  Contesto:
    Dato che "anna" ha la chat Telegram collegata

  Scenario: Posizione aperta
    Dato che il flusso "alfa" vale 312,40 USDC, ha PnL dall'avvio +12,40 USDC, 2 posizioni aperte ed è attivo
    Quando "alfa" apre una posizione long su BTC
    Allora "anna" riceve una notifica che inizia con "🟢 alfa: posizione aperta"
    E i valori della posizione uno per riga
    E in fondo "Flusso: 312,40 USDC · PnL +12,40 USDC · 2 posizioni aperte · attivo"

  Schema dello scenario: Icona per evento
    Dato che il flusso "alfa" vale 312,40 USDC, ha PnL dall'avvio +12,40 USDC, 2 posizioni aperte ed è attivo
    Quando accade <evento> nel flusso "alfa"
    Allora la notifica inizia con "<icona>"

    Esempi:
      | evento                      | icona |
      | chiusura in profitto        | ✅    |
      | chiusura in perdita         | 🔻    |
      | chiusura per stop loss      | 🛑    |
      | chiusura per take profit    | 🎯    |
      | ciclo fallito               | ⚠️    |
      | pausa per errore permanente | ⏸️    |

  Scenario: Stessa notifica per email
    Dato che il flusso "alfa" vale 312,40 USDC, ha PnL dall'avvio +12,40 USDC, 2 posizioni aperte ed è attivo
    E che "anna" riceve le notifiche anche per email
    Quando "alfa" apre una posizione
    Allora l'email ha oggetto "🟢 alfa: posizione aperta" e lo stesso contenuto del messaggio Telegram

  Scenario: Allarme del conto senza stato del flusso
    Dato che il flusso "alfa" vale 312,40 USDC, ha PnL dall'avvio +12,40 USDC, 2 posizioni aperte ed è attivo
    Quando sul conto "test-1" si apre un allarme di riconciliazione
    Allora "anna" riceve una notifica che inizia con "🚨 test-1: allarme di riconciliazione"
    E la notifica non ha lo stato del flusso

  Scenario: Apertura al primo ciclo
    Dato un flusso "alfa" avviato che non ha ancora concluso un ciclo
    Quando al primo ciclo "alfa" apre una posizione su "AVAX"
    Allora la notifica "posizione aperta" termina con lo stato "1 posizione aperta"
    E la riga di stato riporta il valore del flusso dopo l'apertura

  Scenario: Apertura con posizioni già presenti
    Dato che "alfa" ha 1 posizione aperta
    Quando in un ciclo "alfa" apre una posizione su "DOGE"
    Allora la notifica "posizione aperta" termina con lo stato "2 posizioni aperte"

  Scenario: Chiusura dell'unica posizione
    Dato che "alfa" ha 1 posizione aperta
    Quando in un ciclo "alfa" chiude la posizione
    Allora la notifica "posizione chiusa" termina con lo stato "nessuna posizione aperta"

  Scenario: Ordine rifiutato
    Dato che "alfa" ha 1 posizione aperta
    Quando in un ciclo un ordine di "alfa" è rifiutato dall'exchange
    Allora la notifica "ordine rifiutato" termina con lo stato "1 posizione aperta"

  Scenario: Flusso senza alcun valore letto
    Dato un flusso "beta" fermo che non ha mai girato
    Quando parte una notifica di "beta"
    Allora la riga di stato dice "valore non disponibile"
