# ADR 0158 — Menu laterale a gruppi con la voce dell'area attiva

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.1.3 (Task 275)
- Collegate: ADR 0119 (layout con menu laterale ripiegato sul telefono), ADR 0145 (comando Indietro), ADR 0116

## Contesto e problema

Il menu laterale ha la sola voce «Flussi»; conti, storico, chiavi e notifiche si raggiungono da collegamenti in fondo
alla pagina dei flussi. Il proprietario ha scelto il menu Flussi, Conti, Storico e il gruppo Impostazioni con Chiavi e
Notifiche, con etichette generiche.

## Fattori decisionali

- Decisione del proprietario (14 novembre 2026, R2.1.3): voci, gruppo e titoli «Chiavi» e «Notifiche».
- ADR 0119: menu laterale sopra i 768 pixel, pannello ripiegato sotto.
- `tech-dashboard.md`: bulletproof-react; i percorsi vivono in `src/config/paths.ts`.

## Opzioni considerate

### 1. Elenco dichiarativo di gruppi e voci, area attiva per prefisso del percorso

- Pro: una sola struttura nel layout; ogni voce dichiara i percorsi della sua area, e le sotto-pagine accendono la voce
  giusta senza logica nelle pagine.
- Contro: una pagina nuova va aggiunta ai percorsi della sua voce.

### 2. Ogni pagina dichiara la propria voce attiva

- Pro: nessuna regola sui percorsi.
- Contro: diciotto pagine da toccare, e una pagina dimenticata non accende nulla.

## Esito della decisione

Opzione 1. In `dashboard-layout.tsx` la navigazione diventa un elenco di gruppi (`Flussi`, `Conti`, `Storico` senza
intestazione; `Impostazioni` con `Chiavi` e `Notifiche`), ciascuna voce con il suo indirizzo e i prefissi dei percorsi
della sua area (Flussi: `/`, `/flows`, `/ranking`, `/comparison`; le altre il proprio). La voce la cui area contiene il
percorso corrente (`useLocation`) ha `aria-current="page"` e uno stile evidente; la radice `/` vale solo come percorso
esatto. Un gruppo con intestazione è un elenco con la sua etichetta visibile. Le pagine `provider-keys` e
`notifications` si intitolano «Chiavi» e «Notifiche», con le sezioni attuali (fornitori IA, Telegram) sotto un
sottotitolo. Indirizzi invariati.

Verifica: revisione.

### Conseguenze

- Una nuova area si aggiunge con una voce; una nuova sotto-pagina con un prefisso già dichiarato accende la voce da sola.
