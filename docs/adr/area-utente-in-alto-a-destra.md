# ADR area-utente-in-alto-a-destra — Area utente con nome e menu «Esci» nella barra in alto

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 567, Task 568; R6.5.1 (accesso)
- Collegate: ADR 0118 (Entra con MSAL), ADR icone-con-lucide-react-e-comandi-condivisi
- Verifica: prova

## Contesto e problema

«Esci» è l'ultima voce del menu di navigazione (`components/layouts/dashboard-layout.tsx:132-134`,
`sign-out-button.tsx`). Il nome dell'utente non compare da nessuna parte. Il proprietario (17/11/2026) vuole in alto
a destra un'area utente col nome e un menu a tendina che contiene solo Esci.

## Fattori decisionali

- Bug 567. Convenzione delle applicazioni web: account in alto a destra.
- Il nome è già nel token d'identità di MSAL (`account.name`, ripiego `account.username`): nessuna chiamata nuova
  all'API, nessun dato personale nuovo salvato.
- Accessibilità: pulsante con `aria-haspopup="menu"` e `aria-expanded`, chiusura con Esc e clic fuori, focus gestito.

## Decisione

- Nuovo componente `components/layouts/user-menu.tsx` in `AppHeader`, a destra: icona utente e nome (troncato su
  telefono), menu con la sola voce «Esci» che riusa la logica di `SignOutButton` (svuota la cache e `logoutRedirect`).
  Il nome si legge da `lib/auth.tsx` con una funzione `useSignedInUserName()`.
- `NAVIGATION` perde Esci, anche nel menu ripiegato del telefono.
- Prove: nome mostrato, menu che si apre e si chiude da tastiera, Esci che esce.

## Alternative scartate

- Nome da `/me`: l'API non ha il nome e non serve aggiungerlo.

## Conseguenze

- Altre voci dell'utente, se servissero, andranno nello stesso menu.
