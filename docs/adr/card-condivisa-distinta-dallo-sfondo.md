# ADR card-condivisa-distinta-dallo-sfondo — Card condivisa distinta dallo sfondo

- Stato: proposta (23 novembre 2026)
- Requisiti: Bug 726, Task 727
- Collegate: ADR 0116 (struttura della dashboard), ADR tabella-condivisa-senza-sforamento-e-con-filtri, ADR
  icone-con-lucide-react-e-comandi-condivisi (componenti condivisi di `src/components/ui`), `.claude/rules/tech-dashboard.md`
  §Pagine di impostazioni («un riquadro per servizio»)
- Verifica: prova

## Contesto e problema

Lo sfondo delle pagine è `bg-slate-50` (`dashboard-layout.tsx`, `page-layout.tsx`). I riquadri delle funzionalità
scrivono le proprie classi, per esempio `rounded border border-slate-200 p-4`, senza uno sfondo. Il riquadro prende
quindi il colore della pagina e si distingue solo per il bordo sottile, come nella pagina Fonti. Non c'è un componente
card condiviso, e ogni pagina può sbagliare in modo diverso.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): le regole dell'interfaccia stanno in componenti condivisi riusabili, citati
  nelle ADR della UI.
- bulletproof-react: il codice condiviso sta in `src/components`, le funzionalità lo usano.
- Il riquadro si distingue dallo sfondo con il colore, non solo con il bordo.

## Decisione

- Nuovo componente condiviso `Card` in `src/components/ui/card.tsx`: `rounded-lg border border-slate-200 bg-white p-4
  shadow-sm`, con titolo e descrizione facoltativi. Varianti solo per i riquadri di stato che hanno già un colore loro
  (avviso, errore, zona pericolosa), che restano distinti dallo sfondo.
- Ogni riquadro delle funzionalità e delle rotte usa `Card`: fonti, impostazioni (un riquadro per servizio), conti,
  flussi e ogni altro contenitore con bordo e spaziatura interna oggi scritto a mano. `DangerZone` e i riquadri di
  avviso esistenti restano quelli che sono, con il loro sfondo colorato.
- Prova di architettura in `dashboard/architecture/`: un file di `src/features` o `src/app` non scrive un contenitore
  con bordo e spaziatura interna senza uno sfondo. In pratica: le classi `border` con `p-<n>` senza un `bg-` sono
  vietate fuori da `src/components`. La prova è rossa su un esempio che viola e silenziosa su uno conforme.
- Prova: unit test di `Card`; i test delle pagine toccate restano verdi; uno scenario Playwright verifica che la card
  della pagina Fonti abbia uno sfondo diverso da quello della pagina.

## Alternative scartate

- Cambiare lo sfondo della pagina in bianco: le card con il bordo resterebbero poco distinte e senza una regola comune.
- Aggiungere `bg-white` solo nella pagina Fonti: il difetto resterebbe nelle altre pagine e tornerebbe nelle nuove.

## Conseguenze

- Le pagine nuove usano `Card` per i riquadri; la prova di architettura impedisce di riscriverli a mano.
