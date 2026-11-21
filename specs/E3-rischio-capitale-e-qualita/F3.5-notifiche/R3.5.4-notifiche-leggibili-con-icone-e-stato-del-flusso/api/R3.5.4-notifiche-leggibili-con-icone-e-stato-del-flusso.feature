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
    E che il flusso "alfa" vale 312,40 USDC, ha PnL dall'avvio +12,40 USDC, 2 posizioni aperte ed è attivo

  Scenario: Notifica senza flusso
    Quando "anna" chiede la notifica di prova
    Allora la notifica ha icona e titolo e non ha lo stato del flusso
