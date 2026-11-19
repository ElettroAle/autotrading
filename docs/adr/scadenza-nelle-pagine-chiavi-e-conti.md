# ADR scadenza-nelle-pagine-chiavi-e-conti — Scadenza e avviso nelle pagine Chiavi e Conti

- Stato: proposta (19 novembre 2026)
- Requisiti: US 383 R6.2.2, Task 386; dipende da Task 384
- Collegate: ADR scadenza-delle-chiavi-letta-o-indicata, ADR elenco-dei-conti-e-pagina-del-conto, ADR
  icone-con-lucide-react-e-comandi-condivisi; `.claude/rules/tech-dashboard.md` (pagine di impostazioni)
- Verifica: prova

## Contesto e problema

La dashboard non mostra scadenze. R6.2.2 vuole nelle pagine Chiavi e Conti la scadenza di ogni chiave, il campo per
indicarla alla registrazione o dopo, e un avviso visibile finché una chiave in scadenza entro 30 giorni o scaduta non
è rinnovata.

## Fattori decisionali

- Nessuna logica di business nella dashboard: stato e giorni li dà l'API (`expiry_status`, `days_left`,
  `expiry_editable`).
- Componenti condivisi; stato mai solo col colore (regole delle pagine di impostazioni).

## Decisione

- Componente condiviso `KeyExpiryStatus` in `components/ui`: «scadenza sconosciuta» (grigio), «scade il 15/12/2026»,
  «scade tra N giorni» o «scade domani» (attenzione, icona di avviso) e «scaduta» (critica, icona di errore), testo e
  icona sempre insieme.
- Pagina Chiavi (`features/provider-keys`), riga dell'elenco dei conti e scheda Panoramica del conto: lo stato accanto
  alla chiave; con `expiring` o `expired` un avviso persistente in testa alla pagina con il comando per sostituire la
  chiave.
- Campo data facoltativo «Scadenza» nei moduli di registrazione e sostituzione e un comando «Indica scadenza» accanto
  alla chiave, solo con `expiry_editable`; una data letta dall'exchange si mostra come tale.
- Scenari R6.2.2 della dashboard con Playwright sul finto MSW.

## Alternative scartate

- Calcolare i giorni nella dashboard: logica di business fuori dall'API.

## Conseguenze

- Le credenziali degli adapter delle fonti (R4.1.2) useranno lo stesso componente.
