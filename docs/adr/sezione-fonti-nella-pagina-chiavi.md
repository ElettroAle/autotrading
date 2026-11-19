# ADR sezione-fonti-nella-pagina-chiavi — Sezione Fonti in Impostazioni › Chiavi

- Stato: proposta (19 novembre 2026)
- Requisiti: US 314 R4.1.2, Task 316; dipende dal Task 315
- Collegate: ADR credenziali-degli-adapter-delle-fonti, ADR scadenza-nelle-pagine-chiavi-e-conti (componente
  `KeyExpiryStatus`), ADR 0131, ADR icone-con-lucide-react-e-comandi-condivisi; `.claude/rules/tech-dashboard.md`
  (pagine di impostazioni)
- Verifica: prova

## Contesto e problema

La pagina Chiavi (`features/provider-keys`) gestisce le chiavi dei fornitori IA. R4.1.2 vuole in quella pagina una
sezione «Fonti» con gli adapter che richiedono configurazione, i campi dichiarati dall'adapter e i segreti mai in
chiaro.

## Fattori decisionali

- bulletproof-react: nessun import tra funzionalità; la pagina in `src/app` compone le funzionalità.
- Moduli generati dalle dichiarazioni dell'API (ADR 0131), componenti condivisi, stato mai solo col colore.

## Decisione

- Nuova funzionalità `features/source-credentials` (API, componenti, test); la rotta della pagina Chiavi in `src/app`
  mostra sotto le chiavi dei fornitori IA la sezione «Fonti» di questa funzionalità.
- Una riga per adapter che richiede configurazione (da `GET /source-credentials`): fonte e adapter, stato
  «configurato» o «non configurato» con testo e icona, valori non segreti, `KeyExpiryStatus` per la scadenza e i
  comandi «Configura» o «Sostituisci», «Indica scadenza» (solo con `expiry_editable`) e «Rimuovi» con conferma, dai
  componenti condivisi dei comandi. Gli adapter senza configurazione non compaiono; senza adapter da configurare la
  sezione dice «nessun adapter di fonte richiede configurazione».
- Il modulo genera un campo per ogni campo dichiarato: i segreti `type="password"` con `autocomplete="off"`, mai
  precompilati; nella sostituzione i segreti si reinseriscono e i non segreti partono dai valori salvati; campo
  facoltativo «Scadenza».
- Una credenziale rifiutata dal fornitore mostra «rifiutata dal fornitore» con il comando «Sostituisci».
- Responsive: righe come schede impilate sotto i 640 px, nessuno scorrimento orizzontale.
- Scenari R4.1.2 e «Scadenza sconosciuta» di R6.2.2 per la dashboard con Playwright sul finto MSW.

## Alternative scartate

- Mettere le credenziali delle fonti dentro `features/provider-keys`: mescola due contesti dell'API in una
  funzionalità.

## Conseguenze

- L'editor del flusso mostra il motivo «configura l'adapter …» che l'API dà per gli adapter non configurati, senza
  leggere questa funzionalità.
