# ADR pagina-notifiche-a-schede — Pagina Notifiche a schede e pannello del server di posta

- Stato: accettata (17 novembre 2026, design approvato dal proprietario)
- Requisiti: R3.5.5, Task T3.5.5.3; R1.8.1, R3.5.2, R3.5.3
- Collegate: ADR schede-con-aspetto-e-ruolo-di-schede, ADR indirizzo-email-nelle-impostazioni-delle-notifiche, ADR
  scelta-dei-canali-nella-dashboard, ADR icone-con-lucide-react-e-comandi-condivisi, ADR
  invio-dal-server-di-posta-del-tenant
- Verifica: prova

## Contesto e problema

La pagina Notifiche impila Telegram, email e scelta dei canali. Il server di posta aggiunge campi tecnici. Il
proprietario ha scelto due schede e regole UX per le pagine di impostazioni (`.claude/rules/tech-dashboard.md`,
§Pagine di impostazioni, 17/11/2026).

## Fattori decisionali

- `.claude/rules/tech-dashboard.md` §Pagine di impostazioni: preferenze nella vista predefinita, configurazione dei
  servizi in una scheda separata, rimando «Configura», dettagli solo quando servono, stato visibile, stessa forma per
  ogni servizio.
- Componenti condivisi: `ViewTabs`, `CommandButton`, `InputField`, `SelectField`, `FormAlert`, la conferma della
  rimozione già usata dalla zona di emergenza; nessun `<button>` o `<table>` proprio.
- bulletproof-react: tutto nella funzionalità `notifications`; nessun import tra funzionalità.

## Decisione

- Rotta delle notifiche con `ViewTabs` a due schede nella stessa rotta (parametro della vista nell'indirizzo):
  **Preferenze** (predefinita: `NotificationChannelsPanel`, con un avviso in alto e un collegamento «Configura» alla
  scheda Canali quando un canale manca) e **Canali** (con il numero di canali da configurare). Senza nessun canale
  collegato la pagina si apre su Canali.
- Scheda Canali: due riquadri della stessa forma, affiancati da `md` in su, uno sotto l'altro su telefono:
  - **Telegram**: stato in alto, contenuti di oggi (chat collegata, codice di collegamento, notifica di prova);
  - **Email**: stato in alto (collegato con server e indirizzo); passo 1 `MailServerPanel` (form: server, porta,
    sicurezza STARTTLS/TLS, utente, password, mittente, con un aiuto «Gmail: smtp.gmail.com · 587 · STARTTLS ·
    password per le app»; salvato: riassunto di una riga con «password salvata», Modifica e Rimuovi con conferma; in
    modifica la password vuota conserva quella salvata); passo 2 l'indirizzo delle notifiche (disattivato con
    «Configura prima il server di posta» finché il server manca); comando «Invia email di prova» con l'esito accanto,
    compreso il motivo del rifiuto del server.
- API dalla dashboard: `get-mail-server.ts`, `set-mail-server.ts`, `remove-mail-server.ts` con schema zod sulla
  `api-schema.d.ts` rigenerata.

## Alternative scartate

- Una pagina sola con le preferenze in alto: scartata dal proprietario a favore delle schede.
- Preset dei fornitori: non richiesti; l'aiuto testuale basta.

## Conseguenze

- La scelta dei canali, l'operazione frequente, è la prima cosa che l'utente vede.
- La configurazione dei canali ha una forma unica, riusabile per un canale futuro.
